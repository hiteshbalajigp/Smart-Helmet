@echo off
cd /d "%~dp0.."
if not exist database mkdir database
if not exist logs mkdir logs

echo Installing backend dependencies...
pip install fastapi uvicorn pydantic pydantic-settings sqlalchemy aiosqlite PyYAML python-multipart aiofiles httpx -q

echo Starting API on http://127.0.0.1:8000 ...
set HELMET_USE_LOCAL=1
start "Helmet API" cmd /k "cd /d %CD% && set HELMET_USE_LOCAL=1 && python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload"

echo Installing frontend dependencies...
cd frontend
if not exist node_modules call npm install
echo Starting dashboard on http://localhost:5173 ...
start "Helmet Dashboard" cmd /k "cd /d %CD% && npm run dev"

echo.
echo Local stack started:
echo   Dashboard: http://localhost:5173
echo   API docs:  http://127.0.0.1:8000/docs
echo   Health:    http://127.0.0.1:8000/health
pause
