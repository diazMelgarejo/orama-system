import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, mkdir, readFile, writeFile, cp, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import { verifyAssembled } from '../verify-assembled.mjs';
import { listFiles } from '../overlay.mjs';

const root = new URL('../', import.meta.url).pathname;
/** Assemble an isolated candidate with real migrations; register automatic cleanup. */
async function fixture(t) {
  const base = await mkdtemp(path.join(tmpdir(), 'verify-site-')); t.after(() => rm(base, { recursive: true, force: true }));
  const pt = path.join(base, 'pt'), site = path.join(base, 'site');
  await mkdir(path.join(pt, 'packages/prompt-workspace/src'), { recursive: true });
  await cp(path.join(root, 'src/perpetua.mjs'), path.join(pt, 'packages/prompt-workspace/src/index.mjs'));
  await cp(path.join(root, 'src/schema.sql'), path.join(pt, 'packages/prompt-workspace/schema.sql'));
  await mkdir(path.join(site, '.openai'), { recursive: true });
  await writeFile(path.join(site, '.openai/hosting.json'), JSON.stringify({ project_id: 'fixture-project', custom: 'preserve', capabilities: ['other'] }));
  execFileSync(process.execPath, [path.join(root, 'assemble.mjs'), pt, site]);
  await mkdir(path.join(site, 'drizzle/meta'), { recursive: true });
  const sql = await readFile(path.join(root, 'src/schema.sql'), 'utf8');
  await writeFile(path.join(site, 'drizzle/0000_old.sql'), sql.replace('prompt_records_owner_history ON prompt_records(owner_id, archived, created_at, id)', 'prompt_records_owner_active ON prompt_records(owner_id, archived, id)'));
  await writeFile(path.join(site, 'drizzle/0001_history.sql'), 'DROP INDEX prompt_records_owner_active; CREATE INDEX prompt_records_owner_history ON prompt_records(owner_id, archived, created_at, id);');
  await writeFile(path.join(site, 'drizzle/meta/_journal.json'), JSON.stringify({ entries: [{ idx: 0, tag: '0000_old' }, { idx: 1, tag: '0001_history' }] }));
  return { pt, site };
}
/** Snapshot every candidate byte to detect unintended verifier writes. */
async function tree(site) { return Promise.all((await listFiles(site)).map(async file => [file, (await readFile(path.join(site, file))).toString('hex')])); }

test('archived CHECK parity rejects domains that still reject the old probe value 2', async t => {
  const { pt, site } = await fixture(t);
  const migration = path.join(site, 'drizzle/0000_old.sql');
  const original = await readFile(migration, 'utf8');
  for (const constraint of ['archived IN (0, 1, 3)', 'archived IN (0, 1, -1)', 'archived IN (0, 1, 999)', '(archived IN (0, 1)) AND archived = 0']) {
    await writeFile(migration, original.replace('archived IN (0, 1)', constraint));
    const before = await tree(site), result = await verifyAssembled(pt, site);
    assert.equal(result.verified, false, constraint);
    assert.ok(result.errors.some(error => /CHECK.*parity/.test(error)), result.errors.join('; '));
    if (constraint === 'archived IN (0, 1, 3)') assert.ok(result.errors.includes('migration archived CHECK accepts 3'));
    assert.deepEqual(await tree(site), before);
  }
});

test('CHECK parity accepts formatting, identifier quoting and canonical table qualification', async t => {
  const { pt, site } = await fixture(t);
  const migration = path.join(site, 'drizzle/0000_old.sql');
  const original = await readFile(migration, 'utf8');
  await writeFile(migration, original.replace('CHECK(archived IN (0, 1))', 'check ( /* format only */ "prompt_records"."archived" in ( 0 , 1 ) )'));
  assert.deepEqual((await verifyAssembled(pt, site)).errors, []);
});

test('fresh assembly verifies, preserves manifest, is deterministic and read-only', async t => {
  const { pt, site } = await fixture(t), before = await tree(site);
  const result = await verifyAssembled(pt, site);
  assert.deepEqual(result.errors, []); assert.equal(result.verified, true);
  assert.equal(result.migrations.length, 2); assert.ok(result.overlay_sha256);
  assert.deepEqual(await tree(site), before);
  execFileSync(process.execPath, [path.join(root, 'assemble.mjs'), pt, site]);
  assert.deepEqual(await tree(site), before);
  const manifest = JSON.parse(await readFile(path.join(site, '.openai/hosting.json')));
  assert.equal(manifest.project_id, 'fixture-project'); assert.equal(manifest.custom, 'preserve'); assert.ok(manifest.capabilities.includes('other'));
});

test('verifier reports all stale payloads, provenance and manifest errors without writing', async t => {
  const { pt, site } = await fixture(t);
  for (const file of ['app/lib/perpetua.mjs', 'app/lib/server.mjs', 'app/page.tsx']) await writeFile(path.join(site, file), 'stale');
  await writeFile(path.join(site, 'source-provenance.json'), '{}');
  await writeFile(path.join(site, '.openai/hosting.json'), '{}');
  const before = await tree(site), result = await verifyAssembled(pt, site);
  assert.equal(result.verified, false);
  for (const name of ['app/lib/perpetua.mjs', 'app/lib/server.mjs', 'app/page.tsx', 'provenance', 'manifest']) assert.ok(result.errors.some(e => e.includes(name)), name);
  assert.deepEqual(await tree(site), before);
});

test('old migration alone fails parity; missing provenance fails closed', async t => {
  const { pt, site } = await fixture(t);
  await writeFile(path.join(site, 'drizzle/meta/_journal.json'), JSON.stringify({ entries: [{ idx: 0, tag: '0000_old' }] }));
  assert.ok((await verifyAssembled(pt, site)).errors.some(e => /history|index/.test(e)));
  await rm(path.join(site, 'source-provenance.json'));
  assert.ok((await verifyAssembled(pt, site)).errors.some(e => e.includes('provenance')));
});

test('verification cannot attach a disk database from a candidate migration', async t => {
  const { pt, site } = await fixture(t), outside = path.join(site, 'forbidden.sqlite');
  await writeFile(path.join(site, 'drizzle/0001_history.sql'), `ATTACH DATABASE '${outside}' AS disk; CREATE TABLE disk.leak (value TEXT);`);
  const result = await verifyAssembled(pt, site);
  assert.equal(result.verified, false);
  await assert.rejects(readFile(outside), { code: 'ENOENT' });
});

test('non-object provenance and manifests fail closed', async t => {
  const { pt, site } = await fixture(t);
  for (const value of ['null', 'false', '0', '[]']) {
    await writeFile(path.join(site, 'source-provenance.json'), value);
    await writeFile(path.join(site, '.openai/hosting.json'), value);
    const result = await verifyAssembled(pt, site);
    assert.equal(result.verified, false);
    for (const label of ['provenance', 'manifest']) assert.ok(result.errors.some(e => e.includes(label)));
  }
});

test('partial unique index cannot substitute for unconditional request-key uniqueness', async t => {
  const { pt, site } = await fixture(t);
  const sql = await readFile(path.join(root, 'src/schema.sql'), 'utf8');
  const weakened = sql.replace('UNIQUE(owner_id, request_key)', 'CHECK(1)').replace(/CREATE INDEX IF NOT EXISTS prompt_records_owner_history[^;]+;/, 'CREATE UNIQUE INDEX partial_request ON prompt_records(owner_id,request_key) WHERE archived = 1; CREATE INDEX prompt_records_owner_history ON prompt_records(owner_id,archived,created_at,id);');
  await writeFile(path.join(site, 'drizzle/0000_old.sql'), weakened);
  await writeFile(path.join(site, 'drizzle/meta/_journal.json'), JSON.stringify({ entries: [{ idx: 0, tag: '0000_old' }] }));
  assert.equal((await verifyAssembled(pt, site)).verified, false);
});

test('an unjournaled migration file fails because Wrangler would still apply it', async t => {
  const { pt, site } = await fixture(t);
  await writeFile(path.join(site, 'drizzle/0002_extra.sql'), 'SELECT 1;');
  const result = await verifyAssembled(pt, site);
  assert.equal(result.verified, false);
  assert.ok(result.errors.some(error => /files on disk must equal the journal/.test(error)), result.errors.join('; '));
});

test('--index-only-from rejects a rebuild migration and accepts index-only ones', async t => {
  const { pt, site } = await fixture(t);
  assert.deepEqual((await verifyAssembled(pt, site, { indexOnlyFrom: 1 })).errors, []);
  const original = await readFile(path.join(site, 'drizzle/0001_history.sql'), 'utf8');
  await writeFile(path.join(site, 'drizzle/0001_history.sql'), `${original}\n--> statement-breakpoint\nUPDATE prompt_records SET archived = archived;`);
  const result = await verifyAssembled(pt, site, { indexOnlyFrom: 1 });
  assert.equal(result.verified, false);
  assert.ok(result.errors.some(error => /only CREATE\/DROP INDEX/.test(error)), result.errors.join('; '));
  assert.deepEqual((await verifyAssembled(pt, site)).errors, [], 'the guard is opt-in');
});

test('index-only guard cannot be disabled by an invalid or out-of-range index', async t => {
  const { pt, site } = await fixture(t);
  for (const indexOnlyFrom of [-1, 2, 1.5, '1', NaN]) {
    assert.equal((await verifyAssembled(pt, site, { indexOnlyFrom })).verified, false, String(indexOnlyFrom));
  }
});

test('index-only guard rejects DML hidden after a line-comment marker inside a block comment', async t => {
  const { pt, site } = await fixture(t);
  const original = await readFile(path.join(site, 'drizzle/0001_history.sql'), 'utf8');
  await writeFile(path.join(site, 'drizzle/0001_history.sql'), original.replace('CREATE INDEX', 'CREATE INDEX /* -- */') + ' UPDATE prompt_records SET archived = archived;');
  assert.equal((await verifyAssembled(pt, site, { indexOnlyFrom: 1 })).verified, false);
});

test('index-only guard accepts block comments and quoted index names containing semicolons', async t => {
  const { pt, site } = await fixture(t);
  const original = await readFile(path.join(site, 'drizzle/0001_history.sql'), 'utf8');
  await writeFile(path.join(site, 'drizzle/0001_history.sql'), `/* index-only upgrade */ ${original} CREATE INDEX "temporary;--index" ON prompt_records(id); DROP INDEX "temporary;--index";`);
  assert.deepEqual((await verifyAssembled(pt, site, { indexOnlyFrom: 1 })).errors, []);
});
