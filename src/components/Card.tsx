import Image from "next/image";
import Link from "next/link";
import { type Article, formatDate, formats } from "@/lib/news";
import { asset } from "@/lib/site";
import { CardsIcon, PlayIcon, QuestionIcon } from "./Icons";

type Variant = "hero" | "feature" | "photo" | "story" | "color" | "text";

function variantFor(article: Article): Variant {
  if (article.format === "story") return "story";
  if (["cards", "test", "podcast"].includes(article.format)) return "color";
  return article.photo ? "photo" : "text";
}

function FormatIcon({ article }: { article: Article }) {
  if (article.format === "podcast") return <PlayIcon className="card-icon" />;
  if (article.format === "test") return <QuestionIcon className="card-icon" />;
  if (article.format === "cards") return <CardsIcon className="card-icon" />;
  return null;
}

export default function Card({
  article,
  span = 4,
  lead = false,
  priority = false,
}: {
  article: Article;
  span?: 4 | 6 | 8 | 12;
  lead?: boolean;
  priority?: boolean;
}) {
  const variant = lead ? (article.format === "story" ? "feature" : "hero") : variantFor(article);
  const wide = span >= 8;
  const showLead = variant === "text" || wide || variant === "color";

  return (
    <Link
      href={`/news/${article.slug}/`}
      className={`card card-${variant} card-${article.format} span-${span}`}
    >
      {article.photo && variant !== "color" && variant !== "text" && (
        <div className="card-media">
          <Image
            src={asset(article.photo.src)}
            alt={article.photo.alt}
            fill
            sizes={wide ? "(min-width: 1024px) 66vw, 100vw" : "(min-width: 1024px) 33vw, 100vw"}
            priority={priority}
          />
        </div>
      )}
      <div className="card-body">
        <FormatIcon article={article} />
        <h2 className="card-title">{article.title}</h2>
        {showLead && <p className="card-lead">{article.lead}</p>}
        {article.duration && <p className="card-duration">{article.duration}</p>}
        <p className="card-meta">
          <span>{formats[article.format].label}</span>
          <time dateTime={article.publishedAt}>{formatDate(article.publishedAt)}</time>
        </p>
      </div>
    </Link>
  );
}
