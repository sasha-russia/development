import Link from "next/link";
import { type Article, formatDate, rubricLabels } from "@/lib/news";

export default function ArticleCard({ article }: { article: Article }) {
  return (
    <Link href={`/news/${article.slug}/`} className={`card card-${article.rubric}`}>
      <span className="card-rubric">{rubricLabels[article.rubric]}</span>
      <h2 className="card-title">{article.title}</h2>
      <p className="card-lead">{article.lead}</p>
      <time className="card-date" dateTime={article.publishedAt}>
        {formatDate(article.publishedAt)}
      </time>
    </Link>
  );
}
