# OmniRoute

[OmniRoute](https://github.com/diegosouzapw/OmniRoute) — AI-шлюз: один OpenAI-совместимый
эндпоинт (`/v1`) перед множеством провайдеров (Claude, GPT, Gemini и др.) с фолбэками и лимитами.

GitHub Pages отдаёт только статику, поэтому OmniRoute запускается на отдельном сервере
(например, Webdock VPS) или локально.

## Запуск

```bash
cd infra/omniroute
cp .env.example .env
# заполните секреты:
#   JWT_SECRET:              openssl rand -base64 48
#   API_KEY_SECRET:          openssl rand -hex 32
#   STORAGE_ENCRYPTION_KEY:  openssl rand -hex 32
#   INITIAL_PASSWORD:        свой пароль
docker compose up -d
```

- Дашборд: http://localhost:20128 (подключение провайдеров и выпуск API-ключей)
- API: http://localhost:20128/v1

## Безопасность

- Порт слушает только `127.0.0.1`. Наружу открывайте только через reverse proxy с HTTPS
  (Caddy/nginx) и после этого ставьте `AUTH_COOKIE_SECURE=true`.
- `REQUIRE_API_KEY=true`: без ключа запросы к `/v1` не принимаются.
- Ключи OmniRoute никогда не попадают во фронтенд: статический сайт виден всем,
  поэтому любой ключ в его коде будет публичным. Обращаться к шлюзу должен только серверный код
  (сборка в GitHub Actions или будущий бэкенд).
- Версия образа закреплена (`3.8.51`); обновляйте её осознанно.
