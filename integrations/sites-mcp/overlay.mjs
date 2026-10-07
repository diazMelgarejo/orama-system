import { readdir } from 'node:fs/promises';
import path from 'node:path';
export const generatedFiles = ['app/lib/server.mjs', 'app/lib/perpetua.mjs'];
/** List deterministic relative overlay files; reject links and special files. @param {string} dir @param {string} [prefix] @returns {Promise<string[]>} */
export async function listFiles(dir, prefix = '') {
  const found = [];
  for (const entry of await readdir(dir, { withFileTypes: true })) {
    const relative = prefix ? `${prefix}/${entry.name}` : entry.name;
    if (entry.isDirectory()) found.push(...await listFiles(path.join(dir, entry.name), relative));
    else if (entry.isFile()) found.push(relative);
    else throw new Error(`Overlay contains unsupported link or special file: ${relative}`);
  }
  return found.sort();
}
/** Combine reviewed overlay files with generated compiler/server payloads. @param {string} root @returns {Promise<string[]>} */
export async function overlayFiles(root) { return [...new Set([...await listFiles(path.join(root, 'site')), ...generatedFiles])].sort(); }
