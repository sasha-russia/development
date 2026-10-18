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
- `.claude/skills` — skills для Claude Code: `impeccable` (дизайн, `/impeccable …`) и
  `design-taste-frontend` (taste-skill), `animate` (анимации, Emil Kowalski)

## Деплой

Один раз: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
Дальше каждый пуш в `main` публикует сайт.
