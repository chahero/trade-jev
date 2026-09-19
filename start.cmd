@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup.cmd first.
  pause
  exit /b 1
)
if not exist "dist\index.html" (
  echo Run setup.cmd first.
  pause
  exit /b 1
)
echo Jev Trader: http://127.0.0.1:8765
echo Keep this window open for live paper trading. Ctrl+C stops the server.
".venv\Scripts\python.exe" -m uvicorn server.app:app --host 127.0.0.1 --port 8765
