@echo off
setlocal
rem gstack-brain-sync.cmd — Windows shim so cmd.exe (NEEDS_SHELL_ON_WINDOWS) can
rem invoke the bash shebang script. Parallel to the .cmd shims bun creates for
rem gbrain and other tools (gstack issue #1731).
rem
rem bash.exe is NOT on cmd.exe's PATH (it lives in Git for Windows' usr/bin,
rem which is only added to PATH inside a Git Bash session). We resolve it by
rem checking the known Git for Windows locations before falling back to PATH.
set "SCRIPT=%~dp0gstack-brain-sync"

if exist "C:\Program Files\Git\usr\bin\bash.exe" (
    "C:\Program Files\Git\usr\bin\bash.exe" "%SCRIPT%" %*
    exit /b %errorlevel%
)
if exist "C:\Program Files\Git\bin\bash.exe" (
    "C:\Program Files\Git\bin\bash.exe" "%SCRIPT%" %*
    exit /b %errorlevel%
)
rem Last resort: trust PATH (works if Git Bash added itself system-wide)
bash.exe "%SCRIPT%" %*
exit /b %errorlevel%
