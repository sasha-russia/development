---
version: 1
slug: "src-app-page-tsx"
primary_target: "src/app/page.tsx"
related_targets: ["src/app/news/[slug]/page.tsx","src/app/rubric/[format]/page.tsx"]
---

## Scope

Главная лента (`src/app/page.tsx`), страница материала (`src/app/news/[slug]/page.tsx`), страницы рубрик (`src/app/rubric/[format]/page.tsx`). Mode: Read. Build path: code-led (no image generation; Read surface).

Audience and job: жители города с телефона, короткие заходы; понять, что главное сегодня, и открыть один-два материала. Constraints: static export, basePath `/development`, нет бренда Медузы. Pinned by user: устройство страниц meduza.io (светло-серый фон, карточки разной ширины, крупное главное с фото, тёмные карточки историй, цветные карточки тестов/объяснений, колонка коротких новостей, узкая колонка текста в статье); своё: акцент, шрифты, логотип. Photos: open-licensed Wikimedia Commons city photos, credited, labelled as illustrations.

## Direction contract

THESIS: Лента, где формат читается до клика: каждый формат — свой материал карточки (фото, чёрный, жёлтый, синий, белый), а главное занимает две трети первого экрана. Отказ от категории-по-умолчанию: одинаковые белые карточки с превью в сетке.

OWN-WORLD: Холодный светло-серый фон #ebedf0, белые карточки без теней со скруглением 8px, чёрные карточки историй, «троллейбусный» жёлтый #ffd23f для тестов и объяснений, чернильный синий #1c2bd6 для подкастов и акцента. Golos Text (жирный, плотный) — заголовки и интерфейс; Literata — текст статей и лиды. Время в табличных цифрах. Словесный знак-заглушка в шапке.

STORY: Читатель видит главную новость с фото, справа — хронику «Коротко» со временем; ниже понимает по цвету, где история, тест, подкаст; открывает материал и читает спокойную колонку ~65 знаков.

FIRST VIEWPORT: Шапка 56px: знак слева, рубрики в строку, дата справа. Под ней на десктопе сетка 12 колонок: фото-карточка главного на 8 колонок высотой ~520px с заголовком 40px поверх затемнения снизу; колонка «Коротко» на 4 колонки — 6 строк «время + заголовок». На мобильном: главное на всю ширину, затем «Коротко».

FORM: Pinned brief (meduza.io page structure), position 1 of 1; seed:b4d779127b531c17 (user-pinned direction beats the roll)

SIGNATURE: Колонка «Коротко» — хроника с тонкой вертикальной линией времени и меткой самого свежего пункта; движение: фото в карточках мягко приближаются при наведении (ease-out, 400ms), без анимации при prefers-reduced-motion.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
