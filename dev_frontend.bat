@echo off
chcp 65001 >nul
rem AuditXP. Сервер разработки Vite на http://localhost:5173 (API на порту 8000)
cd /d "%~dp0frontend"
if not exist node_modules call npm ci
call npm run dev
