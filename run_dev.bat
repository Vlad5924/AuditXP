@echo off
chcp 65001 >nul
rem AuditXP. Запуск на Windows с базой SQLite и демо-данными
cd /d "%~dp0backend"
if not exist .venv\Scripts\python.exe (
  echo Создание виртуального окружения Python
  py -3 -m venv .venv || python -m venv .venv
  .venv\Scripts\python -m pip install --upgrade pip
  .venv\Scripts\python -m pip install -r requirements.txt
)
if not exist "..\frontend\dist\index.html" (
  echo Клиентская часть не собрана. Выполните build_frontend.bat
)
start "" http://127.0.0.1:8000/
.venv\Scripts\python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
pause
