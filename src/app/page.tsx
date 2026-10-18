import Briefing from "@/components/Briefing";
import Card from "@/components/Card";
import { articles, getArticle } from "@/lib/news";

function pick(slug: string) {
  const article = getArticle(slug);
  if (!article) throw new Error(`Unknown article: ${slug}`);
  return article;
}

export default function Home() {
  const hero = pick("embankment-opening");
  const briefing = articles
    .filter((a) => a.format === "news" && a !== hero && a.slug !== "library-hours")
    .sort((a, b) => b.publishedAt.localeCompare(a.publishedAt))
    .slice(0, 6);

  return (
    <div className="grid">
      <Card article={hero} span={8} lead priority />
      <Briefing items={briefing} />

      <Card article={pick("five-storey")} />
      <Card article={pick("parking-rules")} />
      <Card article={pick("heated-stops")} />

      <Card article={pick("night-embankment")} span={8} lead />
      <Card article={pick("podcast-night-buses")} />

      <Card article={pick("guess-the-district")} />
      <Card article={pick("tram-intervals")} />
      <div className="stack span-4">
        <Card article={pick("school-bus")} />
        <Card article={pick("library-hours")} />
      </div>
    </div>
  );
}
