# Windows PowerShell Runtime Bootstrap

Use this before git pushes, rebases, PR-branch syncs, or test runs on the Windows
RTX/LM Studio host. It keeps the setup frugal: reuse LM Studio's bundled Node and
GitHub Desktop's bundled Git instead of maintaining separate toolchains.

## Bootstrap

```powershell
$lmBin = "$env:USERPROFILE\.lmstudio\bin"
$lmNode = "$env:USERPROFILE\.lmstudio\.internal\utils\node.exe"

$gitRoot = Get-ChildItem "$env:LOCALAPPDATA\GitHubDesktop" -Directory -Filter "app-*" |
  Sort-Object LastWriteTime -Descending |
  Select-Object -First 1 |
  ForEach-Object { Join-Path $_.FullName "resources\app\git" }

$env:PATH = "$lmBin;$gitRoot\mingw64\bin;$gitRoot\cmd;$env:PATH"
$env:GIT_EXEC_PATH = "$gitRoot\mingw64\bin"
$env:npm_config_prefix = "$env:USERPROFILE\.lmstudio"

# Use this Python explicitly; plain `python` may resolve to the Windows Store alias.
$py = "$env:PERPETUA_TOOLS_ROOT\.venv\Scripts\python.exe"
```

## Checks

```powershell
& "$gitRoot\cmd\git.exe" --version
& $lmNode --version
& "$lmBin\npm.cmd" --version
& $py --version
```

## GitHub Desktop Packaging Notes

- `git-remote-https.exe` lives under `mingw64\bin`; missing this path causes
  `git: 'remote-https' is not a git command`.
- Set `GIT_EXEC_PATH` to `mingw64\bin` for child git processes that need helpers.
- The bundle may provide `usr\bin\sh.exe` but no literal `bash.exe`. If a local
  pytest suite invokes `bash`, either install full Git for Windows or create a
  temporary test-only shim:

  ```powershell
  $tmpBashDir = Join-Path $env:TEMP "codex-bash-shim"
  New-Item -ItemType Directory -Force -Path $tmpBashDir | Out-Null
  Copy-Item -Force "$gitRoot\usr\bin\sh.exe" (Join-Path $tmpBashDir "bash.exe")
  $env:PATH = "$tmpBashDir;$gitRoot\usr\bin;$env:PATH"
  ```

- Some shell tests also require `jq`; install it separately or treat those local
  failures as environment failures, not repo regressions.

## PowerShell Gotchas

- Quote upstream shorthand as `git rev-parse --abbrev-ref '@{u}'`; bare `@{u}`
  is parsed as a hashtable.
- Do not rely on `&&` in older Windows PowerShell sessions. Run commands
  separately or use PowerShell-native control flow.
- If the HTTPS helper error disappears and the next failure is a proxy or
  `127.0.0.1` connection error, Git packaging is fixed; investigate network/proxy.
