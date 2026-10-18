# Development

Новостной сайт в духе meduza.io на Next.js (static export), публикуется на GitHub Pages:
https://sasha-russia.github.io/development/

## Разработка

```bash
npm install
npm run dev      # http://localhost:3000
npm run lint
npm run build    # статика в out/
```

## Структура

- `src/app` — страницы (лента, `/news/[slug]`)
- `src/components` — компоненты (шапка, карточки)
- `src/lib/news.ts` — временный источник материалов (позже заменим на CMS)
- `.github/workflows/deploy.yml` — сборка и деплой на GitHub Pages при пуше в `main`
- `infra/omniroute` — AI-шлюз OmniRoute (запускается на отдельном сервере, см. README внутри)

## Деплой

Один раз: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
Дальше каждый пуш в `main` публикует сайт.
