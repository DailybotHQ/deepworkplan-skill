// Fixture-local behavioral and accessibility checks over the built site.
// Zero dependencies by design: every arm gets the same runnable check with no
// install variance. Usage: npm run build && npm run check
// The check asserts the seed's own contract only — it must pass on the
// pristine fixture and fail when a user-visible contract regresses.
import { readdirSync, readFileSync, existsSync, statSync } from 'node:fs';
import { join, relative, resolve } from 'node:path';

const dist = resolve(process.argv[2] ?? 'dist');
let checks = 0;
const failures = [];

function ok(cond, msg) {
	checks++;
	if (!cond) failures.push(msg);
}

function walk(dir) {
	let out = [];
	for (const name of readdirSync(dir)) {
		const p = join(dir, name);
		if (statSync(p).isDirectory()) out = out.concat(walk(p));
		else out.push(p);
	}
	return out;
}

function routeFor(htmlPath) {
	const rel = relative(dist, htmlPath).replace(/\\/g, '/');
	if (rel === 'index.html') return '/';
	if (rel === 'rss.xml') return '/rss.xml';
	if (rel.endsWith('index.html')) return '/' + rel.slice(0, -'index.html'.length);
	return '/' + rel.replace(/\.html$/, '');
}

function fileFor(route) {
	if (route === '/') return join(dist, 'index.html');
	// Direct file: static assets, hashed /_astro output, feeds, sitemaps.
	const direct = join(dist, route.replace(/^\//, ''));
	if (existsSync(direct) && statSync(direct).isFile()) return direct;
	const clean = route.replace(/\/$/, '');
	const asIndex = join(dist, clean, 'index.html');
	if (existsSync(asIndex)) return asIndex;
	const asFile = join(dist, clean + '.html');
	if (existsSync(asFile)) return asFile;
	return null;
}

if (!existsSync(dist)) {
	console.error(`fixture-check: dist not found at ${dist} — run 'npm run build' first`);
	process.exit(1);
}

const htmlFiles = walk(dist).filter((f) => f.endsWith('.html'));
ok(htmlFiles.length >= 5, `expected at least 5 built pages, found ${htmlFiles.length}`);

// Required routes of the seed contract.
for (const route of ['/', '/blog/', '/about/', '/rss.xml']) {
	ok(fileFor(route) !== null, `required route missing: ${route}`);
}

const internalTargets = new Set();
for (const file of htmlFiles) {
	const html = readFileSync(file, 'utf-8');
	const route = routeFor(file);

	// Document contract.
	ok(/<html[^>]*\slang=/.test(html), `${route}: <html> has no lang attribute`);
	ok(/<meta[^>]*name="viewport"/.test(html), `${route}: no viewport meta`);
	ok(/<title>[^<]{3,}<\/title>/.test(html), `${route}: empty or missing <title>`);
	ok(/<meta[^>]*name="description"[^>]*content="[^"]{10,}"/.test(html), `${route}: weak/missing meta description`);

	// Heading contract: exactly one h1, no skipped levels.
	const headings = [...html.matchAll(/<h([1-6])[\s>]/g)].map((m) => Number(m[1]));
	ok(headings.filter((h) => h === 1).length === 1, `${route}: must have exactly one h1 (found ${headings.filter((h) => h === 1).length})`);
	for (let i = 1; i < headings.length; i++) {
		ok(headings[i] - headings[i - 1] <= 1, `${route}: heading level skips from h${headings[i - 1]} to h${headings[i]}`);
	}

	// Image contract: dimensions and text alternative.
	for (const m of html.matchAll(/<img\b[^>]*>/g)) {
		const tag = m[0];
		const src = (tag.match(/\ssrc="([^"]+)"/) || [])[1] ?? '(none)';
		ok(/\swidth="\d+"/.test(tag) && /\sheight="\d+"/.test(tag), `${route}: <img src="${src}"> missing width/height`);
		ok(/\salt(?:="[^"]*")?(?=[\s>])/.test(tag), `${route}: <img src="${src}"> missing alt attribute`);
	}

	// Collect internal links for the resolution check.
	for (const m of html.matchAll(/(?:href|src)="(\/[^"#]*)"/g)) {
		internalTargets.add([route, m[1]]);
	}
}

// Every internal link resolves to a built file.
for (const [from, target] of internalTargets) {
	ok(fileFor(target) !== null, `${from}: internal link ${target} does not resolve in dist/`);
}

console.log(`fixture-check: ${checks} checks over ${htmlFiles.length} pages`);
if (failures.length) {
	console.error(`fixture-check: ${failures.length} failure(s):`);
	for (const f of failures) console.error('  - ' + f);
	process.exit(1);
}
if (checks === 0) {
	console.error('fixture-check: zero checks executed — refusing to pass an empty run');
	process.exit(1);
}
