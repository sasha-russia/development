import { notFound } from "next/navigation";
import { articles, formatDate, getArticle, rubricLabels } from "@/lib/news";

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

  return (
    <article className="article">
      <span className="card-rubric">{rubricLabels[article.rubric]}</span>
      <h1 className="article-title">{article.title}</h1>
      <p className="article-lead">{article.lead}</p>
      <time className="card-date" dateTime={article.publishedAt}>
        {formatDate(article.publishedAt)}
      </time>
      <div className="article-body">
        {article.body.map((p, i) => (
          <p key={i}>{p}</p>
        ))}
      </div>
    </article>
  );
}
