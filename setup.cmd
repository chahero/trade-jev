@echo off
setlocal
cd /d "%~dp0"
set "UV_CACHE_DIR=%CD%\.uv-cache"
uv sync
if errorlevel 1 exit /b 1
call npm ci --cache .npm-cache
if errorlevel 1 exit /b 1
call npm run build
if errorlevel 1 exit /b 1
echo Setup complete. Run start.cmd and open http://127.0.0.1:8765
