export type Rubric = "news" | "story" | "feature" | "podcast";

export type Article = {
  slug: string;
  title: string;
  lead: string;
  rubric: Rubric;
  publishedAt: string;
  body: string[];
};

export const rubricLabels: Record<Rubric, string> = {
  news: "Новости",
  story: "Истории",
  feature: "Разборы",
  podcast: "Подкасты",
};

// Placeholder content until a CMS / content source is connected.
export const articles: Article[] = [
  {
    slug: "launch",
    title: "Мы запускаем новое издание",
    lead: "Рассказываем, каким будет сайт и что появится на нём в ближайшие недели.",
    rubric: "news",
    publishedAt: "2026-10-18T12:00:00+03:00",
    body: [
      "Это тестовая статья. Она нужна, чтобы проверить вёрстку ленты и страницы материала.",
      "Позже материалы будут подгружаться из CMS.",
    ],
  },
  {
    slug: "how-we-work",
    title: "Как устроена редакция",
    lead: "Короткий разбор того, как мы проверяем факты и выбираем темы.",
    rubric: "feature",
    publishedAt: "2026-10-17T09:30:00+03:00",
    body: ["Тестовый текст разбора."],
  },
  {
    slug: "first-story",
    title: "Первая большая история",
    lead: "Пример длинного материала с подзаголовком.",
    rubric: "story",
    publishedAt: "2026-10-16T18:00:00+03:00",
    body: ["Тестовый текст истории."],
  },
];

export function getArticle(slug: string) {
  return articles.find((a) => a.slug === slug);
}

export function formatDate(iso: string) {
  return new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Europe/Moscow",
  }).format(new Date(iso));
}
