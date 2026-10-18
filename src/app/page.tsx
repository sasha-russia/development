import ArticleCard from "@/components/ArticleCard";
import { articles } from "@/lib/news";

export default function Home() {
  const sorted = [...articles].sort((a, b) => b.publishedAt.localeCompare(a.publishedAt));
  return (
    <div className="feed">
      {sorted.map((article) => (
        <ArticleCard key={article.slug} article={article} />
      ))}
    </div>
  );
}
