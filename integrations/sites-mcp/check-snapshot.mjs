import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const pt = process.argv[2];
if (!pt) throw new Error('Usage: node check-snapshot.mjs <PT checkout>');
const here = path.dirname(fileURLToPath(import.meta.url));
for (const [source, target] of [['src/index.mjs', 'perpetua.mjs'], ['schema.sql', 'schema.sql']]) {
  if (!(await readFile(path.join(pt, 'packages/prompt-workspace', source))).equals(await readFile(path.join(here, 'src', target)))) throw new Error(`PT snapshot mismatch: ${source}`);
}
console.log('PT source and schema snapshots are byte-identical');
