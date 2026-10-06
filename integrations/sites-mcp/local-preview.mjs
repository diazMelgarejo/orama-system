/** Opt-in local Worker launcher; never changes the parent host configuration. */
import { existsSync, mkdirSync, readFileSync, statSync, realpathSync } from 'node:fs';
import { createRequire } from 'node:module';
import { execFileSync, spawn } from 'node:child_process';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

/** @param {string} root @returns {void} */
function checkRoot(root) {
  if (!path.isAbsolute(root) || !statSync(root).isDirectory()) throw new Error('Site root must be an absolute existing directory');
}

/** Resolve existing ancestors before creating storage, including symlink aliases. @param {string} target @returns {string} */
function physicalPath(target) {
  let parent = target; const suffix = [];
  while (!existsSync(parent)) { suffix.unshift(path.basename(parent)); parent = path.dirname(parent); }
  return path.join(realpathSync(parent), ...suffix);
}

/** @param {string} siteRoot @param {string} target @returns {void} */
function checkStorage(siteRoot, target) {
  const realRoot = realpathSync(siteRoot), realRuntime = physicalPath(target);
  const relative = path.relative(realRoot, realRuntime);
  if (relative === '' || (!relative.startsWith(`..${path.sep}`) && relative !== '..' && !path.isAbsolute(relative))) {
    let inGit = false;
    try { inGit = execFileSync('git', ['rev-parse', '--is-inside-work-tree'], { cwd: siteRoot, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim() === 'true'; } catch {}
    if (inGit) {
      try { execFileSync('git', ['check-ignore', '--quiet', '--no-index', `${realRuntime}/`], { cwd: realRoot, stdio: 'ignore' }); }
      catch { throw new Error('Runtime directory must be git-ignored; pass --runtime-dir outside the checkout'); }
      const tracked = execFileSync('git', ['ls-files', '--', relative], { cwd: realRoot, encoding: 'utf8' });
      if (tracked.trim()) throw new Error('Runtime directory contains tracked files; choose an external --runtime-dir');
    }
  }
}

/** @param {string} siteRoot @param {NodeJS.ProcessEnv} parentEnv @param {{isolated:boolean,runtimeDir?:string}} options @returns {NodeJS.ProcessEnv} */
export function createPreviewEnv(siteRoot, parentEnv, options) {
  checkRoot(siteRoot);
  const runtime = options.runtimeDir ?? path.join(siteRoot, '.sites-runtime');
  if (!path.isAbsolute(runtime)) throw new Error('Runtime directory must be absolute');
  checkStorage(siteRoot, runtime);
  checkStorage(siteRoot, path.join(runtime, 'd1'));
  const env = { ...parentEnv };
  env.SITES_RUNTIME_ROOT = runtime;
  mkdirSync(path.join(runtime, 'd1'), { recursive: true });
  if (options.isolated) {
    const config = env.XDG_CONFIG_HOME || path.join(runtime, 'xdg-config');
    if (!path.isAbsolute(config)) throw new Error('XDG configuration directory must be absolute');
    checkStorage(siteRoot, config);
    try { mkdirSync(config, { recursive: true }); } catch (error) { throw new Error(`Cannot create configuration directory; repair XDG_CONFIG_HOME or choose an external runtime directory (${error.code})`); }
    env.XDG_CONFIG_HOME = config;
  }
  return env;
}

/** @param {string} siteRoot @param {{port:number,runtimeDir:string}} options @returns {{command:string,args:string[]}} */
export function resolveSiteLaunch(siteRoot, { port, runtimeDir }) {
  checkRoot(siteRoot);
  if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Port must be 1–65535');
  if (!path.isAbsolute(runtimeDir)) throw new Error('Runtime directory must be absolute');
  const require = createRequire(path.join(siteRoot, 'package.json'));
  let pkgPath, pkg;
  try { pkgPath = require.resolve('wrangler/package.json'); pkg = JSON.parse(readFileSync(pkgPath, 'utf8')); } catch { throw new Error('Install Site dependencies using its own package manager; Wrangler is missing'); }
  const entry = path.resolve(path.dirname(pkgPath), typeof pkg.bin === 'string' ? pkg.bin : pkg.bin.wrangler);
  if (!existsSync(entry)) throw new Error('Install Site dependencies; Wrangler entrypoint is missing');
  const preload = path.join(siteRoot, 'scripts/sites-env.mjs');
  if (!existsSync(preload)) throw new Error('Site preload scripts/sites-env.mjs is missing');
  const start = JSON.parse(readFileSync(path.join(siteRoot, 'package.json'), 'utf8')).scripts?.start ?? '';
  if (!start.includes('--import') || !start.includes('scripts/sites-env.mjs')) throw new Error('Unsupported Site preload contract: expected --import scripts/sites-env.mjs');
  const config = path.join(siteRoot, 'dist/server/wrangler.json');
  if (!existsSync(config)) throw new Error('Build the Site before launching its local Worker');
  return { command: process.execPath, args: ['--import', preload, entry, 'dev', '--config', config, '--local', '--persist-to', path.join(runtimeDir, 'd1'), '--ip', '127.0.0.1', '--port', String(port), '--inspector-port', '0'] };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const [root, ...flags] = process.argv.slice(2);
    if (!root) throw new Error('Usage: local-preview.mjs <absolute Site root> [--isolated-config] [--runtime-dir <absolute-dir>] [--port <n>]');
    let isolated = false, runtimeDir = path.join(root, '.sites-runtime'), port = 8787;
    for (let i = 0; i < flags.length; i++) {
      if (flags[i] === '--isolated-config') isolated = true;
      else if (flags[i] === '--runtime-dir' && flags[i + 1]) runtimeDir = flags[++i];
      else if (flags[i] === '--port' && flags[i + 1]) port = Number(flags[++i]);
      else throw new Error(`Unknown or incomplete argument: ${flags[i]}`);
    }
    const env = createPreviewEnv(root, process.env, { isolated, runtimeDir });
    const launch = resolveSiteLaunch(root, { port, runtimeDir });
    const child = spawn(launch.command, launch.args, { cwd: root, env, stdio: 'inherit', shell: false });
    const handlers = new Map(['SIGINT', 'SIGTERM'].map(signal => [signal, () => child.kill(signal)]));
    for (const [signal, handler] of handlers) process.on(signal, handler);
    child.on('error', error => { console.error(error.message); process.exitCode = 1; });
    child.on('exit', (code, signal) => {
      for (const [name, handler] of handlers) process.off(name, handler);
      if (signal) process.kill(process.pid, signal); else process.exitCode = code ?? 1;
    });
  } catch (error) { console.error(error.message); process.exitCode = 1; }
}
