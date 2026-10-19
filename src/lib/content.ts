import { type Article, demoArticles, type Format } from "./news";

// Published articles come from the editorial system when CMS_URL is set at build
// time; otherwise the site builds from the demo content in news.ts.
const cmsUrl = process.env.CMS_URL?.replace(/\/$/, "");

type LexicalNode = { type?: string; text?: string; children?: LexicalNode[] };

type CmsMedia = { url?: string; alt?: string; credit?: string; sourceUrl?: string } | null;

type CmsArticle = {
  slug: string;
  format: Format;
  title: string;
  lead: string;
  publishedAt?: string;
  updatedAt: string;
  featured?: boolean;
  photo?: CmsMedia | number;
  body?: { root?: LexicalNode } | null;
  cards?: { title: string; text: string }[];
  questions?: { text: string; options?: { text: string }[]; answer: number; explanation?: string }[];
  duration?: string;
};

function textOf(node: LexicalNode): string {
  if (node.text) return node.text;
  return (node.children ?? []).map(textOf).join("");
}

// Paragraph-level text from the rich-text editor's JSON.
function paragraphs(body: CmsArticle["body"]): string[] {
  return (body?.root?.children ?? [])
    .map((block) => textOf(block).trim())
    .filter(Boolean);
}

function fromCms(doc: CmsArticle): Article {
  const photo = doc.photo && typeof doc.photo === "object" && doc.photo.url ? doc.photo : null;
  return {
    slug: doc.slug,
    format: doc.format,
    title: doc.title,
    lead: doc.lead,
    publishedAt: doc.publishedAt ?? doc.updatedAt,
    featured: doc.featured ?? false,
    photo: photo
      ? {
          src: photo.url!.startsWith("http") ? photo.url! : `${cmsUrl}${photo.url}`,
          alt: photo.alt ?? "",
          credit: photo.credit ?? "",
          page: photo.sourceUrl ?? "",
        }
      : undefined,
    body: paragraphs(doc.body),
    cards: doc.cards?.length ? doc.cards.map(({ title, text }) => ({ title, text })) : undefined,
    questions: doc.questions?.length
      ? doc.questions.map((q) => ({
          text: q.text,
          options: (q.options ?? []).map((o) => o.text),
          answer: q.answer - 1,
          explanation: q.explanation ?? "",
        }))
      : undefined,
    duration: doc.duration || undefined,
  };
}

async function loadFromCms(): Promise<Article[]> {
  const query = new URLSearchParams({
    "where[_status][equals]": "published",
    depth: "1",
    limit: "500",
    sort: "-publishedAt",
  });
  const res = await fetch(`${cmsUrl}/api/articles?${query}`);
  if (!res.ok) throw new Error(`CMS request failed: ${res.status} ${await res.text()}`);
  const data = (await res.json()) as { docs: CmsArticle[] };
  return data.docs.map(fromCms);
}

let cache: Promise<Article[]> | undefined;

export function getArticles(): Promise<Article[]> {
  cache ??= (cmsUrl ? loadFromCms() : Promise.resolve(demoArticles)).then((list) =>
    [...list].sort((a, b) => b.publishedAt.localeCompare(a.publishedAt)),
  );
  return cache;
}

export async function getArticle(slug: string) {
  return (await getArticles()).find((a) => a.slug === slug);
}

export async function byFormat(format: Format) {
  return (await getArticles()).filter((a) => a.format === format);
}

export const isDemo = !cmsUrl;
