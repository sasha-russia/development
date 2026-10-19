import type { Article } from "./news";

// Picks articles for the home page's fixed slots. Each slot takes the newest
// unused article matching its rule; a slot with no match is left out.
export function homeLayout(all: Article[]) {
  const used = new Set<string>();
  const take = (rule: (a: Article) => boolean) => {
    const found = all.find((a) => !used.has(a.slug) && rule(a));
    if (found) used.add(found.slug);
    return found;
  };

  const hero = take((a) => Boolean(a.featured && a.photo)) ?? take((a) => Boolean(a.photo));
  const briefing = all.filter((a) => a.format === "news" && a !== hero).slice(0, 6);

  const isColor = (a: Article) => a.format === "cards" || a.format === "test";
  const newsWithPhoto = (a: Article) => a.format === "news" && Boolean(a.photo);

  const row2 = [take((a) => a.format === "story"), take(isColor), take(newsWithPhoto)];
  const feature = take((a) => a.format === "story" && Boolean(a.photo));
  const side = take((a) => a.format === "podcast") ?? take(isColor);
  const row4 = [take(isColor), take(newsWithPhoto)];
  const stack = [take((a) => a.format === "news" && !a.photo), take((a) => a.format === "news" && !a.photo)];

  // Everything the slots and the briefing didn't show.
  const inBriefing = new Set(briefing.map((a) => a.slug));
  const more = all.filter((a) => !used.has(a.slug) && !inBriefing.has(a.slug));

  const defined = <T,>(list: (T | undefined)[]) => list.filter((x): x is T => Boolean(x));
  return {
    hero,
    briefing,
    row2: defined(row2),
    feature,
    side,
    row4: defined(row4),
    stack: defined(stack),
    more,
  };
}
