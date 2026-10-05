import assert from 'node:assert/strict';
import test from 'node:test';
import { readFile } from 'node:fs/promises';

// schema.sql is the PT-pinned contract; db/schema.ts is what generates the D1 migration.
// They must declare the same indexes, or a deployed D1 silently lacks the history index.
const snake = name => name.replace(/[A-Z]/g, c => `_${c.toLowerCase()}`);

test('Drizzle schema declares the same indexes as the pinned schema.sql', async () => {
  const sql = await readFile(new URL('../src/schema.sql', import.meta.url), 'utf8');
  const ts = await readFile(new URL('../site/db/schema.ts', import.meta.url), 'utf8');
  const fromSql = new Map([...sql.matchAll(/CREATE INDEX IF NOT EXISTS (\w+) ON prompt_records\(([^)]*)\)/g)]
    .map(([, name, cols]) => [name, cols.split(',').map(c => c.trim())]));
  const fromTs = new Map([...ts.matchAll(/(?<!unique)[iI]ndex\('(\w+)'\)\.on\(([^)]*)\)/g)]
    .filter(([, name]) => !name.endsWith('_request'))
    .map(([, name, cols]) => [name, cols.split(',').map(c => snake(c.trim().replace(/^table\./, '')))]));
  assert.ok(fromSql.size > 0, 'no indexes parsed from schema.sql');
  assert.deepEqual(fromTs, fromSql);
});
