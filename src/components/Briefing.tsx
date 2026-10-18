import Link from "next/link";
import { type Article, formatTime } from "@/lib/news";

// The "Коротко" chronicle: short news as a timeline, newest on top.
export default function Briefing({ items }: { items: Article[] }) {
  return (
    <section className="briefing span-4" aria-labelledby="briefing-title">
      <h2 id="briefing-title" className="briefing-title">
        Коротко
      </h2>
      <ol className="briefing-list">
        {items.map((item, i) => (
          <li key={item.slug} className={i === 0 ? "is-latest" : undefined}>
            <time dateTime={item.publishedAt}>{formatTime(item.publishedAt)}</time>
            <Link href={`/news/${item.slug}/`}>{item.title}</Link>
          </li>
        ))}
      </ol>
      <Link href="/rubric/news/" className="briefing-more">
        Все новости
      </Link>
    </section>
  );
}
