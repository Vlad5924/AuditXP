# AuditXP: Риск-менеджмент

Модуль корпоративного риск-менеджмента на основе данных внутреннего аудита
(ООО «Голдберг-Софт»). Программное средство импортирует проводки из ERP,
очищает данные, выявляет аномалии методом Isolation Forest, оценивает риски
по матрице «вероятность × ущерб», ведет жизненный цикл риска и формирует
отчеты с электронной подписью руководителя.

## Состав проекта

| Каталог | Назначение |
|---|---|
| `backend/` | Серверная часть: FastAPI, SQLAlchemy 2 (asyncio), scikit-learn |
| `backend/app/api` | REST API `/api/v1` (34 ресурса, Swagger на `/api/docs`) |
| `backend/app/etl` | Клиент ERP, очистка, карантин, сопоставление полей |
| `backend/app/ml` | Признаки и стратегии скоринга (Isolation Forest, z-оценка) |
| `backend/app/services` | Бизнес-логика: риски, отчеты, пользователи, уведомления |
| `backend/tests` | 93 автоматических теста (pytest) и 3 теста производительности |
| `frontend/` | Клиентская часть: React 19, TypeScript, Vite |
| `frontend/e2e` | Сценарные тесты интерфейса E2E-01..E2E-09 (Playwright) |
| `db/` | Представления SQL и резервные копии демонстрационной БД |
| `deploy/` | nginx, systemd, Docker Compose, скрипты установки и резервного копирования |
| `samples/` | Пример выгрузки ERP в формате CSV |

## Быстрый запуск в Windows

1. Установите Python 3.12 или новее (флажок «Add python.exe to PATH»).
2. Запустите `run_dev.bat`. При первом запуске создается виртуальное
   окружение и устанавливаются зависимости (3–5 минут).
3. Откроется `http://127.0.0.1:8000/`. База SQLite `backend/auditxp.db`
   создается и заполняется демонстрационными данными автоматически.

Клиентская часть уже собрана в `frontend/dist`. Для повторной сборки
установите Node.js 20+ и выполните `build_frontend.bat`. Режим разработки
с горячей перезагрузкой запускается `dev_frontend.bat` (порт 5173).

## Учетные записи демонстрационной базы

| Роль | Логин | Пароль |
|---|---|---|
| Аудитор | `zhdanko` | `Auditor2026` |
| Аудитор | `litvinova` | `Auditor2026` |
| Руководитель службы | `kovalchuk` | `Chief2026` |
| Администратор | `admin` | `Admin2026` |

## Работа с PostgreSQL

```bash
# создание БД
sudo -u postgres psql
CREATE ROLE auditxp LOGIN PASSWORD 'auditxp';
CREATE DATABASE auditxp WITH OWNER=auditxp ENCODING='UTF8' CONNECTION LIMIT=-1;
GRANT ALL PRIVILEGES ON DATABASE auditxp TO auditxp;
\q
# восстановление демонстрационной копии
pg_restore -v --no-owner --role=auditxp -d auditxp db/backup/auditxp_demo.backup
```

В `backend/.env` укажите
`DATABASE_URL=postgresql+asyncpg://auditxp:auditxp@localhost:5432/auditxp`
(пример всех параметров в `backend/.env.example`).

## Служебные команды

```bash
cd backend
python -m app.cli init-db         # схема, роли, подразделения
python -m app.cli create-admin --email admin@goldberg-soft.by
python -m app.cli seed-demo       # демонстрационные данные
python -m app.cli check           # проверка подключения к БД
python -m scripts.make_sample 2026-11-01 2026-11-03   # пример CSV
```

## Тестирование

```bash
cd backend
pip install -r requirements-dev.txt
pytest -v --cov=app                      # 93 теста, SQLite
TEST_DATABASE_URL=postgresql+asyncpg://auditxp:auditxp@localhost:5432/auditxp_test pytest
pytest -m perf -s                        # тесты производительности PT-01..PT-03
python scripts/benchmark_etl.py --url postgresql+asyncpg://...   # PER-01
python scripts/load_test.py --users 20  # PER-02, PER-03 при запущенном сервере
ruff check app tests scripts
cd ../frontend && npm test && npm run lint
npx playwright install chromium          # один раз для сценарных тестов
npm run e2e -- http://127.0.0.1:8000/    # E2E-01..E2E-09 на демо-базе
```

## Развертывание на сервере

Сценарий для Ubuntu Server 24.04 LTS описан в `deploy/scripts/install.sh`
(PostgreSQL 16, nginx с TLS 1.2/1.3, служба systemd `auditxp-api`).
Альтернатива `cd deploy && docker compose --env-file ../backend/.env up -d`.
Резервное копирование `deploy/scripts/backup.sh`, восстановление
`deploy/scripts/restore.sh`.
