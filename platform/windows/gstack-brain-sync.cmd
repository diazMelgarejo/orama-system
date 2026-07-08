@echo off
setlocal
rem gstack-brain-sync.cmd -- Windows shim so cmd.exe (NEEDS_SHELL_ON_WINDOWS) can
rem invoke the bash shebang script. Parallel to the .cmd shims bun creates for
rem gbrain and other tools (gstack issue #1731).
rem
rem bash.exe is NOT on cmd.exe PATH (lives in Git for Windows usr/bin, added to
rem PATH only inside a Git Bash session). We check known Git locations and the
rem GIT_INSTALL_ROOT env var before falling back to PATH.
set SCRIPT=%~dp0gstack-brain-sync

if defined GIT_INSTALL_ROOT (
    if exist %GIT_INSTALL_ROOT%\usr\bin\bash.exe (
        %GIT_INSTALL_ROOT%\usr\bin\bash.exe %SCRIPT% %*
        exit /b %errorlevel%
    )
)
if exist %PROGRAMFILES%\Git\usr\bin\bash.exe (
    %PROGRAMFILES%\Git\usr\bin\bash.exe %SCRIPT% %*
    exit /b %errorlevel%
)
if exist %LOCALAPPDATA%\Programs\Git\usr\bin\bash.exe (
    %LOCALAPPDATA%\Programs\Git\usr\bin\bash.exe %SCRIPT% %*
    exit /b %errorlevel%
)
if exist %PROGRAMFILES%\Git\bin\bash.exe (
    %PROGRAMFILES%\Git\bin\bash.exe %SCRIPT% %*
    exit /b %errorlevel%
)
rem Last resort: trust PATH (works if Git Bash added itself system-wide)
bash.exe %SCRIPT% %*
exit /b %errorlevel%
