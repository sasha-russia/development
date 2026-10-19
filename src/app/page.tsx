import Briefing from "@/components/Briefing";
import Card from "@/components/Card";
import { getArticles } from "@/lib/content";
import { homeLayout } from "@/lib/layout";

export default async function Home() {
  const { hero, briefing, row2, feature, side, row4, stack, more } = homeLayout(await getArticles());

  return (
    <>
      <div className="grid">
        {hero && <Card article={hero} span={8} lead priority />}
        {briefing.length > 0 && <Briefing items={briefing} />}

        {row2.map((a) => (
          <Card key={a.slug} article={a} />
        ))}

        {feature && <Card article={feature} span={side ? 8 : 12} lead />}
        {side && <Card article={side} />}

        {row4.map((a) => (
          <Card key={a.slug} article={a} />
        ))}
        {stack.length > 0 && (
          <div className="stack span-4">
            {stack.map((a) => (
              <Card key={a.slug} article={a} />
            ))}
          </div>
        )}
      </div>

      {more.length > 0 && (
        <section className="more" aria-labelledby="more-title">
          <h2 id="more-title" className="related-title">
            Ещё
          </h2>
          <div className="grid">
            {more.map((a) => (
              <Card key={a.slug} article={a} />
            ))}
          </div>
        </section>
      )}
    </>
  );
}
