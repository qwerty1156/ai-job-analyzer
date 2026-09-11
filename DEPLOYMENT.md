# Deployment Guide

Пошаговый план деплоя: **Frontend → Vercel**, **Backend → Render** (или Railway),
**PostgreSQL/Redis → managed**. Всё, что можно подготовить заранее (Dockerfile,
`render.yaml`, `vercel.json`, чеклист env vars), уже в репозитории — но сам процесс
деплоя (создание аккаунтов, подключение GitHub, нажатие кнопок в чужих дашбордах)
нужно проделать вам самим: у меня нет доступа к вашим учётным записям.

## 0. Перед деплоем

- Репозиторий должен быть запушен на GitHub (см. `README.md` → раздел GitHub).
- Получите бесплатный ключ Gemini API: https://aistudio.google.com/apikey — он
  понадобится и `api`, и `worker` сервисам.

## 1. Backend → Render (рекомендуемый вариант)

Render умеет разворачивать сразу несколько сервисов из одного `render.yaml`
("Blueprint"). В репозитории он уже есть.

1. Зайдите на https://render.com → **New** → **Blueprint**.
2. Подключите ваш GitHub-репозиторий с этим проектом.
3. Render прочитает `render.yaml` и предложит создать 4 ресурса:
   `ai-job-analyzer-api` (web), `ai-job-analyzer-worker` (background worker),
   `ai-job-analyzer-db` (PostgreSQL), `ai-job-analyzer-redis` (Redis).
4. Нажмите **Apply** — Render соберёт образ по `Dockerfile` и задеплоит все сервисы.
5. **Обязательно вручную впишите `AI_API_KEY`** в Dashboard для *обоих* сервисов
   (`api` и `worker`) — в `render.yaml` он намеренно помечен `sync: false`,
   чтобы секрет не лежал в репозитории.
6. После деплоя скопируйте публичный URL сервиса `api`
   (вида `https://ai-job-analyzer-api.onrender.com`) — он понадобится для
   фронтенда и для CORS (шаг 4).

**Важно:** без сервиса `worker` эндпоинт `POST /analyze` будет вечно висеть в
`pending` — задачи ставятся в очередь, но некому их обрабатывать. Оба сервиса
(`api` и `worker`) должны быть запущены одновременно.

### Альтернатива — Railway

1. https://railway.app → **New Project** → **Deploy from GitHub repo**.
2. Railway сам обнаружит `Dockerfile` и предложит задеплоить `api`.
3. Добавьте **PostgreSQL** и **Redis** через "New" → "Database" в том же проекте
   (Railway создаст переменные окружения автоматически, но их нужно будет
   связать под наши имена — см. раздел 2).
4. Добавьте второй сервис из того же репозитория для `worker`: в настройках
   сервиса задайте **Custom Start Command**:
   `celery -A app.celery_app worker --loglevel=info`.
5. Пропишите переменные окружения (раздел 6) для обоих сервисов.

## 2. PostgreSQL и Redis (managed)

Если используете Render Blueprint (раздел 1) — Postgres и Redis уже включены,
пропустите этот шаг. Если деплоите backend куда-то ещё (Railway, свой сервер) —
подключите managed-провайдеров отдельно, например:

- PostgreSQL: Render Postgres, [Neon](https://neon.tech), Railway Postgres, Supabase.
- Redis: Render Redis, [Upstash](https://upstash.com) (есть бесплатный тариф).

Важно: `DATABASE_URL` в этом проекте использует драйвер **psycopg v3**, поэтому
строка подключения должна начинаться с `postgresql+psycopg://`, а не просто
`postgresql://` — если провайдер выдаёт `postgresql://...`, допишите `+psycopg`
после `postgresql`.

## 3. Frontend → Vercel

1. https://vercel.com → **Add New** → **Project** → импортируйте тот же репозиторий.
2. В `vercel.json` уже указано `"outputDirectory": "frontend"` — Vercel задеплоит
   статический `frontend/index.html` без шага сборки. Framework Preset можно
   оставить "Other" / "No Framework".
3. **До деплоя** откройте `frontend/index.html` и в строке
   `<input id="api-base-input" value="http://localhost:8000" />`
   замените `http://localhost:8000` на реальный URL backend с шага 1
   (например `https://ai-job-analyzer-api.onrender.com`) — так адрес API будет
   правильным по умолчанию, и его не придётся вводить вручную при каждом визите.
   (Поле редактируемо и без этого — это просто удобство.)
4. Нажмите **Deploy**. Получите домен вида `https://ai-job-analyzer.vercel.app`.

## 4. CORS

На backend (`api` сервис) переменная `CORS_ORIGINS` по умолчанию `*` (подходит
для локальной разработки). В проде задайте точный домен фронтенда:

```
CORS_ORIGINS=https://ai-job-analyzer.vercel.app
```

(В `render.yaml` для этого уже есть placeholder — замените
`https://your-frontend.vercel.app` на настоящий домен из шага 3.4.)

## 5. HTTPS

Ничего настраивать не нужно — Render, Railway и Vercel сами выпускают и продлевают
TLS-сертификаты для доменов `*.onrender.com` / `*.up.railway.app` / `*.vercel.app`,
а также для подключённых кастомных доменов (Settings → Domains в каждом дашборде).

## 6. Чеклист переменных окружения для прода

На backend (`api` и `worker`, одинаково для обоих):

| Переменная | Продовое значение |
|---|---|
| `DEBUG` | `false` |
| `AI_PROVIDER` | `gemini` |
| `AI_API_KEY` | ваш реальный ключ (вписать вручную в Dashboard, не в git) |
| `DATABASE_URL` | из managed Postgres, с `+psycopg` |
| `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND` | из managed Redis |
| `JWT_SECRET` | длинная случайная строка (`python -c "import secrets; print(secrets.token_urlsafe(48))"`), **не** дефолтная dev-заглушка |
| `CORS_ORIGINS` | точный домен фронтенда с Vercel |

## 7. Проверка после деплоя

```bash
curl https://<ваш-api-домен>/            # {"status": "ok"}
curl https://<ваш-api-домен>/docs        # Swagger открывается
```

Затем полный сценарий (register → login → analyze → jobs) — см. README.md,
раздел "Основной сценарий использования (curl)", просто подставив прод-домен
вместо `localhost:8000`.
