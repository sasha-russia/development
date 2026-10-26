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
- `src/lib/content.ts` — загрузка материалов: из редакционной системы, если задан `CMS_URL`, иначе демо-материалы из `src/lib/news.ts`
- `cms/` — редакционная система: материалы, задачи, сотрудники, посты в Telegram/ВКонтакте/MAX (см. `cms/README.md`)
- `.github/workflows/deploy.yml` — сборка и деплой на GitHub Pages при пуше в `main`
- `.claude/skills` — skills для Claude Code: `impeccable` (дизайн, `/impeccable …`) и
  `design-taste-frontend` (taste-skill), `animate` (анимации, Emil Kowalski)

## Деплой

Один раз: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
Дальше каждый пуш в `main` публикует сайт.

## Связанные проекты

Раньше лежали в этом репозитории, теперь у каждого свой (закрытый):

- [sasha-russia/speech](https://github.com/sasha-russia/speech) — расшифровщик аудио и видео, speech.a-platonov.ru
- [sasha-russia/social-monitor](https://github.com/sasha-russia/social-monitor) — мониторинг соцсетей городского округа Мытищи, social.a-platonov.ru
