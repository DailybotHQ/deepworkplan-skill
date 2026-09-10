#!/usr/bin/env node
// Recompute the `deepworkplan` entry's computedHash in skills-lock.json from
// the vendored dogfood folder.
//
// Why this exists: `computedHash` is a content hash of the installed skill
// folder — NOT a tag pin. The two addon skills are re-installed (and re-hashed)
// by the release workflow through the real `skills` CLI, but `deepworkplan` is
// deliberately excluded from that refresh because it must mirror THIS working
// revision, not the last published tag. Without this step its hash silently
// goes stale the moment the pack changes.
//
// The algorithm below is copied from the producer, `skills@1.5.24`
// (`dist/cli.mjs` → `computeSkillFolderHash`): sha256 over every file in the
// folder, sorted by `relativePath.localeCompare`, updating the relative path
// then the file content, skipping `.git` and `node_modules`. It is verified
// compatible by reproducing an untouched entry's recorded hash exactly — run
// with `--verify` to check that before writing anything.
//
// It only ever rewrites the `deepworkplan` entry. It never invents a version
// and never touches the addon entries: those belong to the release automation.

import { createHash } from 'node:crypto';
import { readdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, join, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO_ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const LOCK = join(REPO_ROOT, 'skills-lock.json');
const DOGFOOD = join(REPO_ROOT, '.agents', 'skills', 'deepworkplan');
// An entry the release automation owns, used only to prove the algorithm matches.
const CONTROL = { name: 'ai-diff-reviewer', dir: join(REPO_ROOT, '.agents', 'skills', 'ai-diff-reviewer') };

async function collectFiles(baseDir, currentDir, results) {
  const entries = await readdir(currentDir, { withFileTypes: true });
  await Promise.all(entries.map(async (entry) => {
    const fullPath = join(currentDir, entry.name);
    if (entry.isDirectory()) {
      if (entry.name === '.git' || entry.name === 'node_modules') return;
      await collectFiles(baseDir, fullPath, results);
    } else if (entry.isFile()) {
      const content = await readFile(fullPath);
      const relativePath = relative(baseDir, fullPath).split('\\').join('/');
      results.push({ relativePath, content });
    }
  }));
}

async function computeSkillFolderHash(skillDir) {
  const files = [];
  await collectFiles(skillDir, skillDir, files);
  files.sort((a, b) => a.relativePath.localeCompare(b.relativePath));
  const hash = createHash('sha256');
  for (const file of files) {
    hash.update(file.relativePath);
    hash.update(file.content);
  }
  return hash.digest('hex');
}

const raw = await readFile(LOCK, 'utf8');
const lock = JSON.parse(raw);

// 1. Prove the algorithm still matches what the real producer wrote.
const controlRecorded = lock.skills?.[CONTROL.name]?.computedHash;
const controlComputed = await computeSkillFolderHash(CONTROL.dir);
if (controlRecorded !== controlComputed) {
  console.error(`ERROR: algorithm check failed against the '${CONTROL.name}' entry.`);
  console.error(`  recorded: ${controlRecorded}`);
  console.error(`  computed: ${controlComputed}`);
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
console.log(`(algorithm verified against the '${CONTROL.name}' entry)`);
