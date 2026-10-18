"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { type Format, formats } from "@/lib/news";
import { site } from "@/lib/site";

const nav: Format[] = ["news", "story", "cards", "test", "podcast"];

export default function Header({ today }: { today: string }) {
  const pathname = usePathname();

  return (
    <header className="masthead">
      <div className="masthead-inner">
        <Link href="/" className="wordmark" aria-label={`${site.name}, на главную`}>
          <span className="wordmark-mark" aria-hidden />
          {site.name}
        </Link>
        <nav className="masthead-nav" aria-label="Рубрики">
          {nav.map((format) => {
            const href = `/rubric/${format}/`;
            const current = pathname?.startsWith(`/rubric/${format}`);
            return (
              <Link key={format} href={href} aria-current={current ? "page" : undefined}>
                {formats[format].plural}
              </Link>
            );
          })}
        </nav>
        <span className="masthead-date">{today}</span>
      </div>
    </header>
  );
}
