@echo off
chcp 65001 >nul
rem AuditXP. Запуск модульных, интеграционных и системных тестов
cd /d "%~dp0backend"
if not exist .venv\Scripts\python.exe (
  py -3 -m venv .venv
  .venv\Scripts\python -m pip install -r requirements-dev.txt
)
.venv\Scripts\python -m pip install -q -r requirements-dev.txt
.venv\Scripts\python -m pytest -v --cov=app --cov-report=term
cd /d "%~dp0frontend"
if not exist node_modules call npm ci
call npm test
pause
