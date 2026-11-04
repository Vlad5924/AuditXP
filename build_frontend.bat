@echo off
chcp 65001 >nul
rem AuditXP. Сборка клиентской части (нужен Node.js 20 или новее)
cd /d "%~dp0frontend"
call npm ci
call npm run build
pause
