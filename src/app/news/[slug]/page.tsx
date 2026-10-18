import Image from "next/image";
import Link from "next/link";
import { notFound } from "next/navigation";
import Card from "@/components/Card";
import { PlayIcon } from "@/components/Icons";
import Quiz from "@/components/Quiz";
import { articles, formatDate, formats, getArticle } from "@/lib/news";
import { asset } from "@/lib/site";

export function generateStaticParams() {
  return articles.map(({ slug }) => ({ slug }));
}

export async function generateMetadata({ params }: PageProps<"/news/[slug]">) {
  const article = getArticle((await params).slug);
  return article ? { title: article.title, description: article.lead } : {};
}

export default async function ArticlePage({ params }: PageProps<"/news/[slug]">) {
  const article = getArticle((await params).slug);
  if (!article) notFound();

  const related = articles
    .filter((a) => a.slug !== article.slug)
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt))
    .slice(0, 3);

  return (
    <>
      <article className={`article article-${article.format}`}>
        <header className="article-head">
          <h1 className="article-title">{article.title}</h1>
          <p className="article-lead">{article.lead}</p>
          <p className="article-meta">
            <Link href={`/rubric/${article.format}/`}>{formats[article.format].label}</Link>
            <time dateTime={article.publishedAt}>{formatDate(article.publishedAt)}</time>
            {article.duration && <span>{article.duration}</span>}
          </p>
        </header>

        {article.photo && (
          <figure className="article-photo">
            <div className="article-photo-frame">
              <Image
                src={asset(article.photo.src)}
                alt={article.photo.alt}
                fill
                sizes="(min-width: 1100px) 1040px, 100vw"
                priority
              />
            </div>
            <figcaption>
              Иллюстрация.{" "}
              <a href={article.photo.page} target="_blank" rel="noreferrer">
                {article.photo.credit}
              </a>
            </figcaption>
          </figure>
        )}

        <div className="article-body">
          {article.format === "podcast" && (
            <div className="player" role="note">
              <PlayIcon className="player-icon" />
              <div>
                <p className="player-title">Аудио пока нет</p>
                <p>Выпуск появится здесь, когда подключим хостинг подкастов.</p>
              </div>
            </div>
          )}

          {article.body.map((paragraph, i) => (
            <p key={i}>{paragraph}</p>
          ))}

          {article.cards && (
            <ol className="explainer">
              {article.cards.map((card) => (
                <li key={card.title} className="explainer-card">
                  <h2>{card.title}</h2>
                  <p>{card.text}</p>
                </li>
              ))}
            </ol>
          )}

          {article.questions && <Quiz questions={article.questions} />}

          <p className="article-demo">Демонстрационный материал: события и люди вымышлены.</p>
        </div>
      </article>

      <section className="related" aria-labelledby="related-title">
        <h2 id="related-title" className="related-title">
          Читайте также
        </h2>
        <div className="grid">
          {related.map((a) => (
            <Card key={a.slug} article={a} />
          ))}
        </div>
      </section>
    </>
  );
}
