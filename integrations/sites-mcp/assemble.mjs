/** Reproducible assembly: Site starter + Orama overlay + verified PT dependency. */
import { readFile, writeFile, mkdir, cp } from 'node:fs/promises';
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
await cp(path.join(here, 'site'), siteRoot, { recursive: true });
await mkdir(path.join(siteRoot, 'app/lib'), { recursive: true });
await cp(path.join(here, 'src/server.mjs'), path.join(siteRoot, 'app/lib/server.mjs'));
await writeFile(path.join(siteRoot, 'app/lib/perpetua.mjs'), canonical);
const manifestPath = path.join(siteRoot, '.openai/hosting.json');
const manifest = JSON.parse(await readFile(manifestPath, 'utf8'));
manifest.d1 = 'DB'; manifest.capabilities = [...new Set([...(manifest.capabilities || []), 'mcp'])];
await writeFile(manifestPath, JSON.stringify(manifest, null, 2) + '\n');
const provenance = { pt_source_sha256: createHash('sha256').update(canonical).digest('hex'), orama_server_sha256: createHash('sha256').update(await readFile(path.join(here, 'src/server.mjs'))).digest('hex') };
await writeFile(path.join(siteRoot, 'source-provenance.json'), JSON.stringify(provenance, null, 2) + '\n');
console.log(JSON.stringify({ assembled: true, ...provenance }));
