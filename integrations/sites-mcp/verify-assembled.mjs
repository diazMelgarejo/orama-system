/** Read-only release verifier. SQLite is in-memory; no assembly or repair runs here. */
import { readFile, readdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import { DatabaseSync, constants } from 'node:sqlite';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { overlayFiles } from './overlay.mjs';
import { PromptStore } from './src/perpetua.mjs';
const root = path.dirname(fileURLToPath(import.meta.url));
const hash = bytes => createHash('sha256').update(bytes).digest('hex');

/** @param {DatabaseSync} db @returns {object} */
function signature(db) {
  const columns = db.prepare('PRAGMA table_info(prompt_records)').all().map(row => [row.name, row.type.toUpperCase(), row.notnull, row.pk, row.dflt_value]);
  const indexes = db.prepare('PRAGMA index_list(prompt_records)').all().map(row => ({ unique: row.unique, partial: row.partial, columns: db.prepare(`PRAGMA index_info(${JSON.stringify(row.name)})`).all().map(col => col.name) }));
  return { columns, indexes: indexes.sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))) };
}

/** Split SQLite statements without interpreting comments or semicolons inside quoted tokens.
 * @param {string} sql @returns {string[]}
 */
function sqlStatements(sql) {
  const tokens = sql.match(/--[^\r\n]*|\/\*[\s\S]*?\*\/|'(?:''|[^'])*'|"(?:""|[^"])*"|\x60(?:\x60\x60|[^\x60])*\x60|\[[^\]]*\]|[\s\S]/g) ?? [];
  const statements = [];
  let current = '';
  for (const token of tokens) {
    if (token.startsWith('--') || token.startsWith('/*')) current += ' ';
    else if (token === ';') { if (current.trim()) statements.push(current.trim()); current = ''; }
    else current += token;
  }
  if (current.trim()) statements.push(current.trim());
  return statements;
}

/**
 * @param {string} ptRoot @param {string} siteRoot
 * @param {{indexOnlyFrom?: number}} [options] Journal index from which migrations may contain only CREATE/DROP INDEX.
 * @returns {Promise<object>}
 */
export async function verifyAssembled(ptRoot, siteRoot, options = {}) {
  const errors = [], migrations = [], hashes = [];
  const read = async (file, label) => { try { return await readFile(file); } catch (error) { errors.push(`${label}: ${error.code ?? error.message}`); return null; } };
  const same = (a, b, label) => { if (a && b && !a.equals(b)) errors.push(`${label}: bytes differ`); };
  const canonical = await read(path.join(ptRoot, 'packages/prompt-workspace/src/index.mjs'), 'PT compiler');
  const canonicalSchema = await read(path.join(ptRoot, 'packages/prompt-workspace/schema.sql'), 'PT schema');
  const server = await read(path.join(root, 'src/server.mjs'), 'Orama server');
  same(canonical, await read(path.join(root, 'src/perpetua.mjs'), 'Orama compiler'), 'PT/Orama compiler');
  same(canonicalSchema, await read(path.join(root, 'src/schema.sql'), 'Orama schema'), 'PT/Orama schema');
  const files = await overlayFiles(root);
  for (const file of files) {
    const expected = file === 'app/lib/perpetua.mjs' ? canonical : file === 'app/lib/server.mjs' ? server : await read(path.join(root, 'site', file), file);
    const actual = await read(path.join(siteRoot, file), file);
    same(expected, actual, file);
    if (actual) hashes.push([file, hash(actual)]);
  }
  const parse = async (file, label) => {
    const data = await read(file, label); if (!data) return null;
    try {
      const parsed = JSON.parse(data.toString('utf8'));
      if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('object required');
      return parsed;
    } catch { errors.push(`${label}: valid JSON object required`); return null; }
  };
  const provenance = await parse(path.join(siteRoot, 'source-provenance.json'), 'provenance');
  if (provenance && (JSON.stringify(provenance.overlay_files) !== JSON.stringify(files) || provenance.pt_source_sha256 !== (canonical && hash(canonical)) || provenance.orama_server_sha256 !== (server && hash(server)))) errors.push('provenance: list or content hashes differ');
  const manifest = await parse(path.join(siteRoot, '.openai/hosting.json'), 'manifest');
  if (manifest && (manifest.d1 !== 'DB' || !Array.isArray(manifest.capabilities) || !manifest.capabilities.includes('mcp'))) errors.push('manifest: DB binding and mcp capability required');
  const journal = await parse(path.join(siteRoot, 'drizzle/meta/_journal.json'), 'migration journal');
  const candidate = new DatabaseSync(':memory:'), reference = new DatabaseSync(':memory:');
  try {
    // Migration SQL is candidate input. ATTACH (including VACUUM INTO) must never
    // turn an in-memory verification database into a filesystem writer.
    for (const db of [candidate, reference]) db.setAuthorizer(action => action === constants.SQLITE_ATTACH ? constants.SQLITE_DENY : constants.SQLITE_OK);
    if (!canonicalSchema) throw new Error('Canonical schema missing');
    reference.exec(canonicalSchema.toString('utf8'));
    if (!Array.isArray(journal?.entries) || !journal.entries.length) throw new Error('Migration journal empty or invalid');
    if (options.indexOnlyFrom !== undefined && (!Number.isInteger(options.indexOnlyFrom) || options.indexOnlyFrom < 0 || options.indexOnlyFrom >= journal.entries.length)) throw new Error('indexOnlyFrom must name an existing non-negative journal index');
    const seen = new Set();
    for (const [i, entry] of journal.entries.entries()) {
      if (entry.idx !== i || typeof entry.tag !== 'string' || !/^\d{4}_[A-Za-z0-9_-]+$/.test(entry.tag) || seen.has(entry.tag)) throw new Error('Invalid migration journal order or tag');
      seen.add(entry.tag);
      const sql = await read(path.join(siteRoot, 'drizzle', `${entry.tag}.sql`), `migration ${entry.tag}`);
      if (!sql) continue;
      if (Number.isInteger(options.indexOnlyFrom) && i >= options.indexOnlyFrom) {
        const statements = sqlStatements(sql.toString('utf8'));
        if (statements.some(statement => !/^(CREATE\s+(UNIQUE\s+)?INDEX|DROP\s+INDEX)\b/i.test(statement))) errors.push(`migration ${entry.tag}: only CREATE/DROP INDEX statements are allowed from journal index ${options.indexOnlyFrom}`);
      }
      candidate.exec(sql.toString('utf8'));
      migrations.push({ tag: entry.tag, sha256: hash(sql) });
    }
    // Wrangler applies every .sql file in the migrations directory in filename order, not the journal.
    const onDisk = (await readdir(path.join(siteRoot, 'drizzle')).catch(() => [])).filter(name => name.endsWith('.sql')).sort();
    if (JSON.stringify(onDisk) !== JSON.stringify(journal.entries.map(entry => `${entry.tag}.sql`))) errors.push('migrations: .sql files on disk must equal the journal tags, in order');
    if (JSON.stringify(signature(candidate)) !== JSON.stringify(signature(reference))) errors.push('migration schema/index parity differs from canonical history schema');
    const insert = candidate.prepare("INSERT INTO prompt_records (owner_id,id,request_key,original,improved,mode,version,created_at) VALUES ('uniqueness',?,'same-key','o','i','m','v','t')");
    insert.run('first');
    try { insert.run('second'); errors.push('migration request-key uniqueness accepts duplicate active keys'); }
    catch (error) { if (!/UNIQUE constraint failed/.test(error.message)) errors.push(`migration uniqueness probe failed unexpectedly: ${error.message}`); }
    try {
      candidate.prepare("INSERT INTO prompt_records (owner_id,id,request_key,original,improved,mode,version,created_at,archived) VALUES ('probe','probe','probe','o','i','m','v','t',2)").run();
      errors.push('migration archived CHECK accepts 2');
    } catch (error) { if (!/CHECK constraint failed/.test(error.message)) errors.push(`migration CHECK probe failed unexpectedly: ${error.message}`); }
    const plans = [];
    const shim = { prepare(sql) { return { bind(...args) { return { async all() {
      plans.push(candidate.prepare(`EXPLAIN QUERY PLAN ${sql}`).all(...args).map(row => row.detail).join('\n'));
      return { results: candidate.prepare(sql).all(...args) };
    } }; } }; } };
    const store = new PromptStore(shim);
    await store.list('probe');
    await store.list('probe', { before: '2026-10-05T00:00:00.000Z|cursor', limit: 2 });
    if (plans.some(plan => !/USING (COVERING )?INDEX prompt_records_owner_history/.test(plan) || /USE TEMP B-TREE/.test(plan))) errors.push('migration history query does not use history index without temporary sorting');
  } catch (error) { errors.push(`migration verification: ${error.message}`); }
  finally { candidate.close(); reference.close(); }
  return { verified: errors.length === 0, errors, pt_source_sha256: canonical && hash(canonical), orama_server_sha256: server && hash(server), overlay_sha256: hash(JSON.stringify(hashes)), migrations };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2), flag = args.indexOf('--index-only-from');
  const indexOnlyFrom = flag === -1 ? undefined : Number(args.splice(flag, 2)[1]);
  const [pt, site] = args;
  if (args.length !== 2 || !pt || !site || (flag !== -1 && (!Number.isInteger(indexOnlyFrom) || indexOnlyFrom < 0))) { console.error('Usage: verify-assembled.mjs <PT checkout> <Site root> [--index-only-from <journal index>]'); process.exitCode = 1; }
  else { const result = await verifyAssembled(pt, site, { indexOnlyFrom }); console.log(JSON.stringify(result)); process.exitCode = result.verified ? 0 : 1; }
}
