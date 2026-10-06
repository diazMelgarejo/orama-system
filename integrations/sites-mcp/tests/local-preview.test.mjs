import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, symlinkSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { execFileSync, spawnSync, spawn } from 'node:child_process';
import { createPreviewEnv, resolveSiteLaunch } from '../local-preview.mjs';

function fixture(t) {
  const site = mkdtempSync(path.join(tmpdir(), 'site with spaces '));
  t.after(() => rmSync(site, { recursive: true, force: true }));
  for (const dir of ['scripts', 'node_modules/wrangler/bin', 'dist/server']) mkdirSync(path.join(site, dir), { recursive: true });
  writeFileSync(path.join(site, 'package.json'), JSON.stringify({ type: 'module', scripts: { start: 'node --import ./scripts/sites-env.mjs ./node_modules/wrangler/bin/wrangler.js dev --config dist/server/wrangler.json' } }));
  writeFileSync(path.join(site, 'scripts/sites-env.mjs'), '');
  writeFileSync(path.join(site, 'node_modules/wrangler/package.json'), JSON.stringify({ name: 'wrangler', bin: { wrangler: 'bin/wrangler.js' } }));
  writeFileSync(path.join(site, 'node_modules/wrangler/bin/wrangler.js'), 'process.exit(7)');
  writeFileSync(path.join(site, 'dist/server/wrangler.json'), '{}');
  return site;
}

test('isolated configuration is child scoped and preserves explicit configuration', t => {
  const site = fixture(t);
  const parent = { HOME: '/home/developer', HTTP_PROXY: 'proxy', HTTPS_PROXY: 'secure', NO_PROXY: 'local', NODE_EXTRA_CA_CERTS: 'ca', SSL_CERT_FILE: 'ssl' };
  const original = { ...parent };
  const env = createPreviewEnv(site, parent, { isolated: true });
  assert.equal(env.XDG_CONFIG_HOME, path.join(site, '.sites-runtime/xdg-config'));
  for (const key of Object.keys(parent)) assert.equal(env[key], parent[key]);
  assert.deepEqual(parent, original);
  assert.equal(createPreviewEnv(site, { ...parent, XDG_CONFIG_HOME: '' }, { isolated: true }).XDG_CONFIG_HOME, env.XDG_CONFIG_HOME);
  const explicit = path.join(site, 'explicit');
  assert.equal(createPreviewEnv(site, { XDG_CONFIG_HOME: explicit }, { isolated: true }).XDG_CONFIG_HOME, explicit);
  const ordinary = createPreviewEnv(site, parent, { isolated: false });
  assert.equal(ordinary.XDG_CONFIG_HOME, parent.XDG_CONFIG_HOME);
  for (const key of Object.keys(parent)) assert.equal(ordinary[key], parent[key]);
  assert.equal(ordinary.SITES_RUNTIME_ROOT, path.join(site, '.sites-runtime'));
});

test('invalid paths fail without silently replacing caller configuration', t => {
  const site = fixture(t);
  assert.throws(() => createPreviewEnv('relative', {}, { isolated: true }), /absolute/);
  assert.throws(() => createPreviewEnv(site, { XDG_CONFIG_HOME: 'relative' }, { isolated: true }), /absolute/);
  const file = path.join(site, 'file'); writeFileSync(file, 'x');
  assert.throws(() => createPreviewEnv(site, { XDG_CONFIG_HOME: path.join(file, 'config') }, { isolated: true }), /configuration/);
});

test('runtime state inside a worktree must be ignored', t => {
  const site = fixture(t); execFileSync('git', ['init', '-q', site]);
  assert.throws(() => createPreviewEnv(site, {}, { isolated: true }), /ignored/);
  writeFileSync(path.join(site, '.gitignore'), '/.sites-runtime/\n');
  assert.doesNotThrow(() => createPreviewEnv(site, {}, { isolated: true }));
  const outside = mkdtempSync(path.join(tmpdir(), 'runtime-'));
  t.after(() => rmSync(outside, { recursive: true, force: true }));
  assert.doesNotThrow(() => createPreviewEnv(site, {}, { isolated: true, runtimeDir: outside }));
});

test('runtime aliases cannot conceal unignored state inside the Site', t => {
  const site = fixture(t); execFileSync('git', ['init', '-q', site]);
  const outside = mkdtempSync(path.join(tmpdir(), 'site-alias-'));
  t.after(() => rmSync(outside, { recursive: true, force: true }));
  symlinkSync(site, path.join(outside, 'alias'));
  assert.throws(() => createPreviewEnv(site, {}, { isolated: true, runtimeDir: path.join(outside, 'alias/unignored') }), /ignored/);
});

test('ignored runtime roots do not permit symlinked D1 or config writes to unignored source', t => {
  const site = fixture(t); execFileSync('git', ['init', '-q', site]);
  writeFileSync(path.join(site, '.gitignore'), '/.sites-runtime/\n');
  mkdirSync(path.join(site, '.sites-runtime')); mkdirSync(path.join(site, 'source-state'));
  symlinkSync(path.join(site, 'source-state'), path.join(site, '.sites-runtime/d1'));
  assert.throws(() => createPreviewEnv(site, {}, { isolated: true }), /ignored/);
  rmSync(path.join(site, '.sites-runtime/d1'));
  symlinkSync(path.join(site, 'source-state'), path.join(site, '.sites-runtime/xdg-config'));
  assert.throws(() => createPreviewEnv(site, {}, { isolated: true }), /ignored/);
});

test('launch resolves Site dependencies and local-only arguments; CLI propagates exit', t => {
  const site = fixture(t), runtimeDir = path.join(site, '.sites-runtime');
  const launch = resolveSiteLaunch(site, { port: 8787, runtimeDir });
  assert.equal(launch.command, process.execPath);
  assert.ok(launch.args.includes('127.0.0.1')); assert.ok(launch.args.includes(path.join(runtimeDir, 'd1')));
  assert.ok(!launch.args.includes('--remote'));
  assert.equal(spawnSync(process.execPath, [new URL('../local-preview.mjs', import.meta.url).pathname, site, '--isolated-config'], { encoding: 'utf8' }).status, 7);
  writeFileSync(path.join(site, 'node_modules/wrangler/bin/wrangler.js'), "process.kill(process.pid, 'SIGTERM')");
  assert.equal(spawnSync(process.execPath, [new URL('../local-preview.mjs', import.meta.url).pathname, site, '--isolated-config'], { encoding: 'utf8' }).signal, 'SIGTERM');
  rmSync(path.join(site, 'scripts/sites-env.mjs'));
  assert.throws(() => resolveSiteLaunch(site, { port: 8787, runtimeDir }), /preload/);
  rmSync(path.join(site, 'node_modules/wrangler'), { recursive: true });
  assert.throws(() => resolveSiteLaunch(site, { port: 8787, runtimeDir }), /dependencies/);
});

test('prepared Wrangler reproduces HOME configuration failure and isolated readiness', { skip: !process.env.SITES_MCP_SITE_ROOT, timeout: 45000 }, async t => {
  const site = process.env.SITES_MCP_SITE_ROOT;
  const runtime = mkdtempSync(path.join(tmpdir(), 'wrangler-reproduction-'));
  t.after(() => rmSync(runtime, { recursive: true, force: true }));
  const home = path.join(runtime, 'synthetic-home'); writeFileSync(home, 'regular file');
  const launch = resolveSiteLaunch(site, { port: 18977, runtimeDir: runtime });
  async function probe(isolated) {
    const parent = { ...process.env, HOME: home, SITES_RUNTIME_ROOT: runtime, WRANGLER_LOG_PATH: path.join(runtime, 'logs'), WRANGLER_REGISTRY_PATH: path.join(runtime, 'registry'), MINIFLARE_REGISTRY_PATH: path.join(runtime, 'miniflare') };
    delete parent.XDG_CONFIG_HOME;
    const env = createPreviewEnv(site, parent, { isolated, runtimeDir: runtime });
    const child = spawn(launch.command, launch.args, { cwd: site, env, detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
    let output = '', done = false;
    const exit = new Promise(resolve => child.once('exit', () => { done = true; resolve(); }));
    child.stdout.on('data', data => { output += data; }); child.stderr.on('data', data => { output += data; });
    try {
      for (let i = 0; i < 100 && !done && !output.includes('Ready on'); i++) await new Promise(resolve => setTimeout(resolve, 200));
      return output;
    } finally {
      if (!done) { process.kill(-child.pid, 'SIGTERM'); await Promise.race([exit, new Promise(resolve => setTimeout(resolve, 3000))]); }
      if (!done) { process.kill(-child.pid, 'SIGKILL'); await exit; }
    }
  }
  const ordinary = await probe(false);
  assert.match(ordinary, /ENOTDIR|ENOENT/); assert.match(ordinary, /\.config|\.wrangler/);
  const isolated = await probe(true); assert.match(isolated, /Ready on/);
});
