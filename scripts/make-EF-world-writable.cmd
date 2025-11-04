@echo off
setlocal ENABLEDELAYEDEXPANSION
set SCRIPT_DIR=%~dp0
set PS1=%SCRIPT_DIR%make-EF-world-writable.ps1

rem Launch PowerShell with execution policy bypass and no profile
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%PS1%" %*

endlocal
