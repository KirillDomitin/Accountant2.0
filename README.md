# Accountant2

Веб-сервис для получения данных об организациях из ЕГРЮЛ и автоматического отслеживания изменений.

**Продакшн:** https://acc.404.mn

---

## Что делает сервис

- Поиск организации по ИНН через ЕГРЮЛ API
- Генерация готового `.docx`-документа с реквизитами
- Отслеживание изменений (название, директор, адрес, ОКВЭД, уставный капитал)
- Ежедневная автоматическая проверка всех отслеживаемых ИНН
- История запросов с атрибуцией по пользователю
- JWT-аутентификация с refresh-токенами, rate limiting, управление пользователями

---

## Стек

| Слой | Технологии |
|---|---|
| Backend API | Python 3.13, FastAPI, SQLAlchemy (async), Alembic |
| Auth | JWT (PyJWT), bcrypt, Redis (refresh-токены) |
| БД | PostgreSQL 17 |
| Кэш / очереди | Redis 7 |
| Планировщик | APScheduler |
| Frontend | React (Vite) |
| Веб-сервер | Nginx (reverse proxy + auth_request) |
| Контейнеризация | Docker, Docker Compose |
| Пакетный менеджер | uv |

---

## Архитектура

```
Browser
  └── Nginx
        ├── /auth/*         → auth-service :8001
        ├── /api/v1/*       → backend :8000  (через nginx auth_request)
        └── /*              → frontend (статика)

backend
  └── API → Service → Repository → PostgreSQL
                  └── Redis (кэш ЕГРЮЛ, временные данные)

auth-service
  └── API → Service → PostgreSQL (пользователи)
                  └── Redis (refresh-токены, rate limiting)
```

Каждый запрос к `/api/v1/*` проходит через `auth_request` к `auth-service/auth/validate`. При успехе nginx проксирует заголовки `X-User-Id` и `X-User-Role` в backend.

---

## Структура репозитория

```
.
├── backend/                 # Основной API-сервис
│   ├── app/
│   │   ├── api/v1/          # HTTP-эндпоинты
│   │   ├── services/        # Бизнес-логика
│   │   ├── repositories/    # Доступ к БД
│   │   ├── models/          # SQLAlchemy-модели
│   │   ├── schemas/         # Pydantic-схемы
│   │   └── core/            # Конфиг, логирование, исключения
│   ├── tests/
│   └── alembic/
├── auth-service/            # Сервис аутентификации
│   ├── app/
│   └── alembic/
├── frontend/                # React SPA
├── nginx/                   # Конфиги nginx (dev + prod)
├── .github/workflows/       # CI/CD
├── docker-compose.yml       # Dev окружение
└── docker-compose.prod.yml  # Prod окружение
```

---

## Локальный запуск

### Требования

- Docker + Docker Compose
- Python 3.13 (для запуска тестов вне Docker)
- [uv](https://docs.astral.sh/uv/)

### 1. Клонировать и настроить окружение

```bash
git clone https://github.com/KirillDomitin/Accountant2.0.git
cd Accountant2.0
cp .env.example .env
```

Заполнить `.env`:

```env
# PostgreSQL
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=accountant2

# Backend
DATABASE_URL=postgresql+asyncpg://postgres:postgres@postgres:5432/accountant2
REDIS_URL=redis://redis:6379/0
EGRUL_CACHE_TTL=7200
EGRUL_API_BASE_URL=https://egrul.org
DEBUG=false

# Auth
SECRET_KEY=<вывод: python -c "import secrets; print(secrets.token_hex(32))">
ADMIN_EMAIL=admin@example.com
ADMIN_PASSWORD=changeme123
```

### 2. Поднять сервисы

```bash
docker compose up --build
```

Сервисы будут доступны:

| Сервис | URL |
|---|---|
| Frontend | http://localhost |
| Backend API | http://localhost/api/v1 |
| Auth API | http://localhost/auth |
| Backend (прямой) | http://localhost:8000 |
| Auth (прямой) | http://localhost:8001 |

### 3. Применить миграции

```bash
# Backend
docker compose exec backend uv run alembic upgrade head

# Auth-service
docker compose exec auth-service uv run alembic upgrade head
```

После старта `auth-service` автоматически создаёт admin-пользователя из `ADMIN_EMAIL` / `ADMIN_PASSWORD`, если БД пуста.

---

## API

### Аутентификация

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/auth/login` | Вход. Возвращает `access_token`, ставит refresh-cookie |
| `POST` | `/auth/refresh` | Обновить access-токен по refresh-cookie |
| `POST` | `/auth/logout` | Выход, инвалидация refresh-токена |
| `GET` | `/auth/validate` | Внутренний эндпоинт nginx auth_request |
| `POST` | `/auth/users` | Создать пользователя (admin) |
| `GET` | `/auth/users` | Список пользователей (admin) |
| `PATCH` | `/auth/users/{id}` | Активировать / деактивировать (admin) |

Все запросы к `/api/v1/*` требуют заголовок:
```
Authorization: Bearer <access_token>
```

### Backend

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/api/v1/inn/lookup` | Поиск по ИНН, скачать `.docx` |
| `GET` | `/api/v1/history` | История запросов |
| `GET` | `/api/v1/history/{id}` | Детали запроса |
| `POST` | `/api/v1/tracking` | Добавить ИНН в отслеживание |
| `POST` | `/api/v1/tracking/bulk` | Добавить несколько ИНН сразу |
| `GET` | `/api/v1/tracking` | Список отслеживаемых ИНН |
| `GET` | `/api/v1/tracking/{inn}` | Детали с историей изменений |
| `DELETE` | `/api/v1/tracking/{inn}` | Снять с отслеживания |
| `POST` | `/api/v1/tracking/{inn}/check` | Принудительная проверка |
| `POST` | `/api/v1/tracking/{inn}/confirm` | Подтвердить изменения |
| `GET` | `/health` | Healthcheck |

### Пример: получить документ по ИНН

```bash
# 1. Логин
TOKEN=$(curl -s -X POST https://acc.404.mn/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"changeme123"}' \
  | jq -r '.access_token')

# 2. Скачать .docx
curl -X POST https://acc.404.mn/api/v1/inn/lookup \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"inn":"7709383684"}' \
  -o organization.docx
```

---

## Логирование

Логи пишутся в директорию `logs/` с ежедневной ротацией:

| Файл | Уровень | Хранение |
|---|---|---|
| `logs/app.log` | INFO и выше | 30 дней |
| `logs/error.log` | ERROR и выше | 90 дней |

Консоль — INFO и выше.

---

## Тесты

```bash
cd backend
uv sync --group dev
uv run pytest --tb=short -q
```

Покрытие:
- `test_egrul_parser.py` — парсинг ответов ЕГРЮЛ (чистые функции)
- `test_egrul_client.py` — HTTP-клиент (кэш, ошибки API, мок httpx)
- `test_tracking_service.py` — бизнес-логика отслеживания (мок репозиториев)

---

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`):

```
push / PR → master
  ├── Lint / backend      (ruff)
  ├── Lint / auth-service (ruff)  } параллельно
  └── Test / backend      (pytest)

  ↓ все прошли + ветка master

  Deploy → SSH на сервер → git pull + docker compose up --build
```

### Необходимые GitHub Secrets

| Secret | Описание |
|---|---|
| `SERVER_HOST` | IP продакшн-сервера |
| `SSH_PRIVATE_KEY` | Приватный SSH-ключ для доступа к серверу |

---

## Деплой (продакшн)

### Первичная настройка сервера

```bash
# На сервере (один раз)
git clone https://github.com/KirillDomitin/Accountant2.0.git /root/app
cp /root/app/.env.example /root/app/.env
# Заполнить .env реальными значениями

cd /root/app
docker compose -f docker-compose.prod.yml up --build -d
docker compose -f docker-compose.prod.yml exec backend uv run alembic upgrade head
docker compose -f docker-compose.prod.yml exec auth-service uv run alembic upgrade head
```

### SSL (Let's Encrypt)

```bash
docker run --rm \
  -v /root/certbot/conf:/etc/letsencrypt \
  -v /root/certbot/www:/var/www/certbot \
  certbot/certbot certonly --webroot \
  -w /var/www/certbot -d acc.404.mn \
  --email your@email.com --agree-tos --no-eff-email
```

После получения сертификата перезапустить nginx:

```bash
docker compose -f docker-compose.prod.yml restart nginx
```

### Продакшн-конфиг

- Nginx: HTTPS, HTTP→HTTPS редирект, rate limiting (10 req/s API, 3 req/s auth)
- Все сервисы: `restart: unless-stopped`
- PostgreSQL данные: `postgres_data` volume

---

## Разработка

### Добавить новый эндпоинт (workflow)

1. Определить домен и входные/выходные данные
2. Добавить Pydantic-схемы в `schemas/`
3. Реализовать бизнес-логику в `services/`
4. Реализовать доступ к БД в `repositories/`
5. Создать миграцию: `uv run alembic revision --autogenerate -m "описание"`
6. Добавить HTTP-эндпоинт в `api/v1/endpoints/`
7. Написать тесты для сервиса

### Создать миграцию

```bash
docker compose exec backend uv run alembic revision --autogenerate -m "add_new_table"
docker compose exec backend uv run alembic upgrade head
```
