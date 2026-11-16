#!/usr/bin/env node
// Recompute the `deepworkplan` entry's computedHash in skills-lock.json from
// the vendored dogfood folder.
//
// Why this exists: `computedHash` is a content hash of the installed skill
// folder — NOT a tag pin. The two addon skills are re-installed (and re-hashed)
// by the release workflow through the real `skills` CLI, but `deepworkplan` is
// never installed from a tag because it must mirror THIS working revision.
// scripts/refresh-dogfood-skill.sh runs this after every copy — on a PR, and
// in both release workflows right after the version stamp — so the hash never
// goes stale when the pack changes.
//
// Two producer algorithms are implemented, both copied from the `skills` CLI
// (`computeSkillFolderHash`):
//   - v1, `skills@1.5.24`: sha256 over every file, sorted by
//     `relativePath.localeCompare`, updating the relative path then the file
//     content, skipping `.git` and `node_modules`.
//   - v2, `skills@1.9.0`: files sorted by the UTF-8 bytes of their path; per
//     file `path NUL length NUL content`, CRLF normalized to LF in text files;
//     skips `metadata.json` files and `.git`, `__pycache__`, `__pypackages__`
//     directories; follows a symlink only when it resolves inside the folder.
// The release workflow re-installs the addon skills with whatever CLI version
// npx resolves, so the lockfile can carry either. The helper picks the
// algorithm that reproduces an untouched entry's recorded hash exactly, and
// refuses to write when neither does. Run with `--verify` to check that
// before writing anything.
//
// It only ever rewrites the `deepworkplan` entry. It never invents a version
// and never touches the addon entries: those belong to the release automation.

import { createHash } from 'node:crypto';
import { readdir, readFile, realpath, stat, writeFile } from 'node:fs/promises';
import { dirname, join, relative, resolve, sep } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const LOCK = join(REPO_ROOT, 'skills-lock.json');
const DOGFOOD = join(REPO_ROOT, '.agents', 'skills', 'deepworkplan');
// An entry the release automation owns, used only to prove the algorithm matches.
const CONTROL = { name: 'ai-diff-reviewer', dir: join(REPO_ROOT, '.agents', 'skills', 'ai-diff-reviewer') };

// v1 — skills@1.5.24
async function collectFilesV1(baseDir, currentDir, results) {
  const entries = await readdir(currentDir, { withFileTypes: true });
  await Promise.all(entries.map(async (entry) => {
    const fullPath = join(currentDir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === '.git' || entry.name === 'node_modules') return;
      await collectFilesV1(baseDir, fullPath, results);
    } else if (entry.isFile()) {
      const content = await readFile(fullPath);
      const relativePath = relative(baseDir, fullPath).split('\\').join('/');
      results.push({ relativePath, content });
    }
  }));
}

async function hashV1(skillDir) {
  const files = [];
  await collectFilesV1(skillDir, skillDir, files);
  files.sort((a, b) => a.relativePath.localeCompare(b.relativePath));
  const hash = createHash('sha256');
  for (const file of files) {
    hash.update(file.relativePath);
    hash.update(file.content);
  }
  return hash.digest('hex');
}

// v2 — skills@1.9.0
const V2_EXCLUDE_FILES = new Set(['metadata.json']);
const V2_EXCLUDE_DIRS = new Set(['.git', '__pycache__', '__pypackages__']);
const v2Excluded = (name, isDirectory) =>
  V2_EXCLUDE_FILES.has(name) || (isDirectory && V2_EXCLUDE_DIRS.has(name));

function normalizeLineEndings(content) {
  if (content.includes(0) || !content.includes('\r\n')) return content;
  return Buffer.from(content.toString('latin1').replaceAll('\r\n', '\n'), 'latin1');
}

async function collectFilesV2(dir, prefix, root, ancestors, results) {
  const realDir = await realpath(dir);
  if (ancestors.has(realDir)) return;
  const branch = new Set(ancestors).add(realDir);
  const entries = await readdir(dir, { withFileTypes: true });
  await Promise.all(entries.map(async (entry) => {
    if (v2Excluded(entry.name, entry.isDirectory())) return;
    const fullPath = join(dir, entry.name);
    const path = prefix + entry.name;
    let isDirectory = entry.isDirectory();
    if (entry.isSymbolicLink()) {
      const target = await realpath(fullPath).catch(() => null);
      if (!target || (target !== root && !target.startsWith(root + sep))) return;
      isDirectory = (await stat(target)).isDirectory();
      if (isDirectory && v2Excluded(entry.name, true)) return;
    } else if (!isDirectory && !entry.isFile()) return;
    if (isDirectory) await collectFilesV2(fullPath, `${path}/`, root, branch, results);
    else results.push({ path, content: await readFile(fullPath) });
  }));
}

async function hashV2(skillDir) {
  const files = [];
  await collectFilesV2(skillDir, '', await realpath(skillDir), new Set(), files);
  const entries = files.map((f) => ({
    path: Buffer.from(f.path.split('\\').join('/'), 'utf-8'),
    content: normalizeLineEndings(f.content),
  }));
  entries.sort((a, b) => Buffer.compare(a.path, b.path));
  const hash = createHash('sha256');
  for (const { path, content } of entries) {
    hash.update(path);
    hash.update('\0');
    hash.update(String(content.length));
    hash.update('\0');
    hash.update(content);
  }
  return hash.digest('hex');
}

const ALGORITHMS = [['skills@1.9.0', hashV2], ['skills@1.5.24', hashV1]];

const raw = await readFile(LOCK, 'utf8');
const lock = JSON.parse(raw);

// 1. Prove which producer algorithm wrote the lockfile.
const controlRecorded = lock.skills?.[CONTROL.name]?.computedHash;
let computeSkillFolderHash = null;
let algorithmName = '';
const tried = [];
for (const [name, fn] of ALGORITHMS) {
  const value = await fn(CONTROL.dir);
  tried.push(`${name}: ${value}`);
  if (value === controlRecorded) { computeSkillFolderHash = fn; algorithmName = name; break; }
}
if (!computeSkillFolderHash) {
  console.error(`ERROR: algorithm check failed against the '${CONTROL.name}' entry.`);
  console.error(`  recorded: ${controlRecorded}`);
  for (const line of tried) console.error(`  computed (${line})`);
  console.error('Refusing to write a hash this script cannot prove is compatible.');
  console.error("Re-install through the real 'skills' CLI instead.");
  process.exit(1);
}

const recorded = lock.skills?.deepworkplan?.computedHash;
const computed = await computeSkillFolderHash(DOGFOOD);

if (process.argv.includes('--verify')) {
  if (recorded === computed) {
    console.log('skills-lock.json: deepworkplan computedHash is current.');
    process.exit(0);
  }
  console.error('skills-lock.json: deepworkplan computedHash is STALE.');
  console.error(`  recorded: ${recorded}`);
  console.error(`  computed: ${computed}`);
  console.error('Run: node scripts/update-dogfood-lock.mjs');
  process.exit(1);
}

if (recorded === computed) {
  console.log('skills-lock.json already current — nothing to do.');
  process.exit(0);
}

lock.skills.deepworkplan.computedHash = computed;
await writeFile(LOCK, `${JSON.stringify(lock, null, 2)}\n`, 'utf8');
console.log(`skills-lock.json: deepworkplan computedHash ${recorded} -> ${computed}`);
console.log(`(algorithm ${algorithmName}, verified against the '${CONTROL.name}' entry)`);
