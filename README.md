# AI Job Analyzer

Production-like backend (+ простой frontend), который анализирует, насколько
кандидат подходит вакансии — по вручную введённым навыкам или по загруженному
резюме (PDF/DOCX) — и объясняет результат: что совпадает, чего не хватает и что
стоит подтянуть.

## What it does

1. Пользователь регистрируется и логинится (JWT).
2. Загружает резюме (PDF/DOCX) — сервис извлекает текст и достаёт из него навыки,
   опыт и образование (через AI или встроенную эвристику).
3. Вставляет текст вакансии и запускает сопоставление.
4. Получает: процент соответствия, список совпавших и недостающих навыков,
   пробелы по опыту, конкретные рекомендации и краткий разбор вакансии.
5. Может вернуться к истории прошлых анализов в любой момент.

## Features

- Анализ вакансии по списку навыков — асинхронно, через очередь (`POST /analyze` → `202` → `GET /jobs/{id}`).
- Анализ резюме против вакансии с собственным **scoring engine**: AI только
  извлекает факты (0.0–1.0 по 5 измерениям), итоговый процент считает backend
  по прозрачной взвешенной формуле — не «AI так сказал».
- Загрузка резюме (PDF/DOCX) с автоматическим извлечением навыков, опыта и образования.
- История анализов, привязанная к пользователю (JWT-авторизация).
- Redis-кэш: одинаковая вакансия + одинаковые навыки не гоняются в AI повторно.
- Structured output вместо парсинга текста: LLM обязан вернуть строго
  типизированный JSON, который сразу валидируется Pydantic.
- Понятные HTTP-коды ошибок (400/401/404/409/429/500/503) — ни один плохой
  запрос или сбой AI не роняет сервис.
- Структурированное логирование без утечки секретов (API-ключей, паролей, токенов).
- Простой веб-интерфейс (vanilla HTML/CSS/JS, без сборки).
- Полностью поднимается одной командой: `docker compose up`.

## Tech Stack

| Слой | Технологии |
|---|---|
| API | FastAPI, Pydantic v2, Uvicorn |
| AI | Google Gemini API (structured output / `response_schema`) |
| БД | PostgreSQL, SQLAlchemy 2.0 (`psycopg` v3) |
| Кэш / брокер очереди | Redis |
| Фоновые задачи | Celery |
| Авторизация | JWT (`PyJWT`), `passlib[bcrypt]` |
| Парсинг резюме | `pypdf`, `python-docx` |
| Тесты | `pytest`, SQLite in-memory, мокнутый Celery |
| Frontend | Чистый HTML/CSS/JS, без фреймворков |
| Инфраструктура | Docker, Docker Compose |
| Деплой | Render/Railway (backend), Vercel (frontend) |

## Architecture

```
                     ┌────────────────────────────────────────────┐
                     │                  FastAPI                   │
                     │                                            │
POST /register ──────┼──▶ app/api/auth.py ──▶ services/security   │
POST /login    ──────┤                                            │
GET  /me       ──────┤                                            │
                     │                                            │
POST /analyze  ──────┼──▶ services/analyzer.enqueue_analysis()    │
                     │        └─▶ Job (PostgreSQL, status=pending)│
                     │        └─▶ Celery .delay() ──▶ 202 Accepted│
                     │                                            │
GET  /jobs/{id}──────┼──▶ читает статус Job / готовый Analysis    │
GET  /analyses ──────┼──▶ история анализов текущего пользователя  │
GET  /analyses/{id}──┤                                            │
                     │                                            │
POST /resume   ──────┼──▶ services/resume_service                 │
                     │        PDF/DOCX → extract → clean → AI     │
                     │        → skills → PostgreSQL (Resume)      │
                     │                                            │
POST /match    ──────┼──▶ services/matching                       │
                     │        AI → extraction (факты 0.0-1.0)     │
                     │        Backend → scoring engine (decision) │
                     └────────────────────────────────────────────┘
                              │                    │
                     ┌────────▼─────────┐  ┌───────▼────────┐
                     │  Celery worker    │  │   PostgreSQL   │
                     │  process_analysis_│  │ users/resumes/ │
                     │  job:              │  │ analyses/jobs │
                     │  Redis? → AI/      │  └────────────────┘
                     │  fallback → БД     │
                     └────────┬───────────┘
                              │
                        ┌─────▼─────┐
                        │   Redis   │  кэш + брокер Celery
                        └───────────┘

Frontend (frontend/index.html) ──HTTP/JSON──▶ FastAPI (CORS разрешён)
```

**Ключевой архитектурный принцип:** `AI → extraction, backend → decision`.
Модель никогда не считает финальные бизнес-решения (итоговый процент
соответствия) — она только извлекает факты в строго заданном формате
(`response_schema`), а решение (`match_percent`) принимает прозрачная
формула в `app/services/scoring.py`.

**Про `POST /analyze` vs `POST /match`:** `/analyze` — асинхронный (создаёт
`Job`, отвечает `202`, результат и ошибки AI видны через `GET /jobs/{id}` как
`status: failed` + `error_message`). `/resume` и `/match` — синхронные:
там сбои AI сразу возвращаются HTTP-кодом (429/503/500). Осознанный выбор:
`/analyze` — самый частый и потенциально долгий путь, вынесен в фон;
`/resume`/`/match` — разовые операции с одним файлом/одним запросом, где
мгновенный ответ уместнее.

## API

Автогенерируемый Swagger: `<backend-url>/docs`. Кратко:

| Метод | Путь | Авторизация | Описание |
|---|---|:---:|---|
| GET | `/` | нет | health-check |
| POST | `/register` | нет | регистрация (email + пароль) |
| POST | `/login` | нет | логин → JWT `access_token` |
| GET | `/me` | да | текущий пользователь |
| POST | `/analyze` | да | поставить анализ вакансии в очередь → `202` + `job_id` |
| GET | `/jobs/{id}` | да | статус задачи: `pending`/`processing`/`completed`/`failed` |
| GET | `/analyses` | да | история анализов (сводка) |
| GET | `/analyses/{id}` | да | полная запись анализа |
| POST | `/resume` | да | загрузить резюме (PDF/DOCX) → извлечённые навыки |
| POST | `/match` | да | сопоставить резюме с вакансией (свой scoring engine) |

Коды ошибок:

| Ситуация | HTTP | `error` |
|---|:---:|---|
| Невалидные входные данные (пустая/длинная вакансия, пустой `skills`, битый файл резюме) | 400 | `invalid_request` |
| Нет/невалиден токен, неверный email/пароль | 401 | `unauthorized` |
| Ресурс не найден / принадлежит другому пользователю | 404 | `not_found` |
| Email уже занят | 409 | `conflict` |
| Лимит запросов к AI (`/resume`, `/match`) | 429 | `ai_rate_limited` |
| AI недоступен / нет ключа / таймаут | 503 | `ai_service_unavailable` / `ai_timeout` |
| AI ответил не тем форматом | 500 | `ai_invalid_response` |

## Local Setup

### Вариант A — Docker (рекомендуется)

```bash
docker compose up --build
```

Поднимает всё: `api` (:8000), `worker` (Celery), `db` (PostgreSQL :5432),
`redis` (:6379), `frontend` (:3000).

- Swagger: http://localhost:8000/docs
- Веб-интерфейс: http://localhost:3000

### Вариант B — без Docker

Нужны локально запущенные PostgreSQL и Redis (или `docker compose up db redis`
только для них).

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # и при желании отредактировать
```

Терминал 1:
```bash
uvicorn app.main:app --reload
```

Терминал 2 (обязателен, иначе `/analyze` будет вечно висеть в `pending`):
```bash
celery -A app.celery_app worker --loglevel=info
```

Фронтенд — просто откройте `frontend/index.html` в браузере.

### Включить настоящий AI-анализ

По умолчанию `AI_PROVIDER=none` — сервис работает на встроенной keyword-логике,
без ключей. Чтобы включить AI: получите бесплатный ключ на
https://aistudio.google.com/apikey, в `.env` укажите `AI_PROVIDER=gemini` и
`AI_API_KEY=...`, перезапустите `api` и `worker`.

> Почему Gemini, а не Anthropic API: у Anthropic нет постоянного бесплатного
> тарифа (только платный pay-per-token), а у Google Gemini есть настоящий
> бесплатный тариф (модели Flash/Flash-Lite). Интеграция с провайдером
> изолирована в `app/services/ai.py` — переключить на другой LLM несложно.

## Environment Variables

| Переменная | Назначение | По умолчанию |
|---|---|---|
| `AI_PROVIDER` | `none` (без AI) или `gemini` | `none` |
| `AI_API_KEY` | Ключ Gemini API | пусто |
| `AI_MODEL` | Модель Gemini | `gemini-2.5-flash` |
| `AI_TIMEOUT_SECONDS` | Таймаут запроса к AI | `30` |
| `MIN_VACANCY_LENGTH` / `MAX_VACANCY_LENGTH` | Ограничения длины текста вакансии | `10` / `8000` |
| `MAX_RESUME_SIZE_MB` | Максимальный размер файла резюме | `5` |
| `DATABASE_URL` | Строка подключения PostgreSQL (`+psycopg`) | `postgresql+psycopg://postgres:postgres@localhost:5432/ai_job_analyzer` |
| `REDIS_URL` | Redis для кэша | `redis://localhost:6379/0` |
| `CACHE_TTL_SECONDS` | TTL кэша анализа | `3600` |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | Redis для очереди Celery | `redis://localhost:6379/0` |
| `JWT_SECRET` | Секрет подписи JWT — **сменить в проде** | dev-заглушка |
| `JWT_ALGORITHM` | Алгоритм подписи | `HS256` |
| `JWT_EXPIRE_MINUTES` | Время жизни токена | `1440` |
| `CORS_ORIGINS` | Разрешённые origin'ы через запятую | `*` |

Полный шаблон — `.env.example`. Реальный `.env` **никогда** не коммитится
(см. `.gitignore`) — секреты только через переменные окружения.

## Docker

```bash
docker compose up --build
```

`docker-compose.yml` включает 5 сервисов: `api`, `worker`, `db` (Postgres),
`redis`, `frontend` (nginx, отдаёт статику). `Dockerfile` — общий для `api` и
`worker` образ (разный `command` в compose).

## Tests

```bash
pip install -r requirements.txt
pytest -v
```

Используется **SQLite in-memory** вместо реального PostgreSQL (быстро,
изолированно, без поднятой инфраструктуры) и мокнутый Celery `.delay()` —
реальный Redis-брокер для тестов не нужен.

```
tests/
├── test_auth.py          # регистрация, логин, /me, включая защиту от утечки пароля в логах
├── test_analyze.py       # валидный/невалидный запрос, пустые данные, ошибка AI, authorization
├── test_analyses.py      # история анализов, изоляция между пользователями
├── test_resume.py        # загрузка и парсинг резюме (PDF/DOCX)
├── test_match.py         # resume ↔ vacancy matching, ошибки AI (429/503/500)
├── test_scoring.py       # unit-тесты scoring engine
├── test_celery_task.py   # выполнение Celery-задачи (task.apply(), без брокера)
└── test_health.py
```

## Deployment

Frontend → Vercel, backend → Render/Railway, PostgreSQL и Redis → managed.
Подробный пошаговый гайд, готовые конфиги (`render.yaml`, `vercel.json`) и
чеклист production-переменных — в **[DEPLOYMENT.md](./DEPLOYMENT.md)**.

Коротко: HTTPS — автоматически на всех трёх платформах; CORS — выставить
`CORS_ORIGINS` на точный домен фронтенда; секреты — только через переменные
окружения дашборда, никогда не в git.

## Future Improvements

После MVP, но не раньше (см. `DEPLOYMENT.md`) — по убыванию приоритета:

- CV improvement — конкретные правки резюме под вакансию.
- Job recommendations — подбор вакансий под резюме, а не только наоборот.
- Skill roadmap — персональный план обучения на основе пробелов.
- Salary estimation.
- Job comparison — сравнение нескольких вакансий между собой.
- ATS-style resume check — проверка на проходимость через ATS-фильтры.
- Rate limiting и usage limits на уровне самого API (не только проброс 429 от AI).
- Analytics — агрегированная статистика по анализам пользователя.
- Alembic-миграции вместо `create_all()` при старте.
- Ретраи с backoff для сбоев AI в Celery-задаче.
- Refresh-токены / отзыв токенов.
- WebSocket/SSE вместо поллинга `GET /jobs/{id}`.
