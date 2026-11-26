@echo off
setlocal
rem The execution policy applies to this process only.
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-html.ps1" %*
set "sss_result=%ERRORLEVEL%"
if not "%sss_result%"=="0" (
  echo.
  echo Startup stopped. Read the instructions above.
  pause
)
exit /b %sss_result%
