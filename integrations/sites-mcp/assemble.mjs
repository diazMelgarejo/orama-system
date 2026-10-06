/** Reproducible assembly: Site starter + Orama overlay + verified PT dependency. */
import { readFile, writeFile, mkdir, cp, rm, readdir, lstat } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const [ptRoot, siteRoot] = process.argv.slice(2);
if (!ptRoot || !siteRoot) throw new Error('Usage: node assemble.mjs <PT checkout> <prepared Site starter>');
const here = path.dirname(fileURLToPath(import.meta.url));
const canonical = await readFile(path.join(ptRoot, 'packages/prompt-workspace/src/index.mjs'));
const pinned = await readFile(path.join(here, 'src/perpetua.mjs'));
if (!canonical.equals(pinned)) throw new Error('PT source differs from the reviewed snapshot; sync and review before assembly');
const canonicalSchema = await readFile(path.join(ptRoot, 'packages/prompt-workspace/schema.sql'));
if (!canonicalSchema.equals(await readFile(path.join(here, 'src/schema.sql')))) throw new Error('PT schema differs from reviewed snapshot');
/** @param {string} dir @param {string} [prefix] @returns {Promise<string[]>} POSIX-style relative file paths. */
async function listFiles(dir, prefix = '') {
  const found = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) found.push(...await listFiles(path.join(dir, entry.name), relative));
    else found.push(relative);
  }
  return found.sort();
}
const generated = ['app/lib/server.mjs', 'app/lib/perpetua.mjs'];
const overlayFiles = [...new Set([...await listFiles(path.join(here, 'site')), ...generated])].sort();
// Remove files a previous assembly owned but the current overlay no longer contains, so the
// candidate equals the reviewed overlay. Starter files are never listed here and are never touched.
const provenancePath = path.join(siteRoot, 'source-provenance.json');
let previous = [];
try { previous = JSON.parse(await readFile(provenancePath, 'utf8')).overlay_files ?? []; } catch (error) { if (error.code !== 'ENOENT') throw error; }
for (const stale of previous.filter(file => !overlayFiles.includes(file))) {
  const target = path.resolve(siteRoot, stale);
  if (path.isAbsolute(stale) || !target.startsWith(path.resolve(siteRoot) + path.sep)) throw new Error(`Refusing to remove path outside the Site: ${stale}`);
  // The check above is lexical. Refuse when any directory between the Site root and the target is
  // a symlink, since rm would follow it out of the Site. (rm on the target itself unlinks a link.)
  let dir = path.resolve(siteRoot);
  for (const part of path.relative(dir, path.dirname(target)).split(path.sep).filter(Boolean)) {
    dir = path.join(dir, part);
    const info = await lstat(dir).catch(error => { if (error.code === 'ENOENT') return null; throw error; });
    if (!info) break; // ancestor already gone: nothing to remove
    if (info.isSymbolicLink()) throw new Error(`Refusing to remove through a symlinked directory: ${stale}`);
  }
  await rm(target, { force: true });
}
await cp(path.join(here, 'site'), siteRoot, { recursive: true });
await mkdir(path.join(siteRoot, 'app/lib'), { recursive: true });
await cp(path.join(here, 'src/server.mjs'), path.join(siteRoot, 'app/lib/server.mjs'));
await writeFile(path.join(siteRoot, 'app/lib/perpetua.mjs'), canonical);
const manifestPath = path.join(siteRoot, '.openai/hosting.json');
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
manifest.d1 = 'DB'; manifest.capabilities = [...new Set([...(manifest.capabilities || []), 'mcp'])];
await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
const provenance = { overlay_files: overlayFiles, pt_source_sha256: createHash('sha256').update(canonical).digest('hex'), orama_server_sha256: createHash('sha256').update(await readFile(path.join(here, 'src/server.mjs'))).digest('hex') };
await writeFile(provenancePath, JSON.stringify(provenance, null, 2) + '\n');
console.log(JSON.stringify({ assembled: true, overlay_file_count: overlayFiles.length, pt_source_sha256: provenance.pt_source_sha256, orama_server_sha256: provenance.orama_server_sha256 }));
