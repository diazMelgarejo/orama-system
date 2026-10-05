import assert from 'node:assert/strict';
import test from 'node:test';
import { execFile } from 'node:child_process';
import { promisify } from 'node:util';
import { mkdtemp, mkdir, writeFile, readFile, cp, access } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const run = promisify(execFile);
const here = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(here, '..');
const exists = file => access(file).then(() => true, () => false);

async function fixtures() {
  const base = await mkdtemp(path.join(tmpdir(), 'sites-assemble-'));
  const pt = path.join(base, 'pt/packages/prompt-workspace');
  await mkdir(path.join(pt, 'src'), { recursive: true });
  await cp(path.join(root, 'src/perpetua.mjs'), path.join(pt, 'src/index.mjs'));
  await cp(path.join(root, 'src/schema.sql'), path.join(pt, 'schema.sql'));
  const site = path.join(base, 'site');
  await mkdir(path.join(site, '.openai'), { recursive: true });
  await writeFile(path.join(site, '.openai/hosting.json'), JSON.stringify({ capabilities: [] }));
  await writeFile(path.join(site, 'starter.txt'), 'starter-owned');
  return { pt: path.join(base, 'pt'), site };
}

test('reassembly removes stale overlay files but keeps starter files', async () => {
  const { pt, site } = await fixtures();
  await run('node', [path.join(root, 'assemble.mjs'), pt, site]);
  assert.equal(await exists(path.join(site, 'app/lib/server.mjs')), true);
  // Simulate a file from an earlier overlay that the current overlay no longer ships.
  await writeFile(path.join(site, 'app/stale.tsx'), 'stale');
  const provenancePath = path.join(site, 'source-provenance.json');
  const provenance = JSON.parse(await readFile(provenancePath, 'utf8'));
  provenance.overlay_files.push('app/stale.tsx');
  await writeFile(provenancePath, JSON.stringify(provenance));
  await run('node', [path.join(root, 'assemble.mjs'), pt, site]);
  assert.equal(await exists(path.join(site, 'app/stale.tsx')), false);
  assert.equal(await readFile(path.join(site, 'starter.txt'), 'utf8'), 'starter-owned');
  assert.equal(JSON.parse(await readFile(path.join(site, '.openai/hosting.json'), 'utf8')).d1, 'DB');
});

test('assembly refuses a recorded path that escapes the Site and a drifted PT snapshot', async () => {
  const { pt, site } = await fixtures();
  await run('node', [path.join(root, 'assemble.mjs'), pt, site]);
  const provenancePath = path.join(site, 'source-provenance.json');
  const provenance = JSON.parse(await readFile(provenancePath, 'utf8'));
  provenance.overlay_files.push('../outside.txt');
  await writeFile(provenancePath, JSON.stringify(provenance));
  await assert.rejects(run('node', [path.join(root, 'assemble.mjs'), pt, site]), /outside the Site/);
  await writeFile(path.join(pt, 'packages/prompt-workspace/src/index.mjs'), '// drift\n');
  await assert.rejects(run('node', [path.join(root, 'assemble.mjs'), pt, site]), /reviewed snapshot/);
});
