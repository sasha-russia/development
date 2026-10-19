import type { Metadata } from "next";
import { Golos_Text, Literata } from "next/font/google";
import Footer from "@/components/Footer";
import Header from "@/components/Header";
import { getArticles } from "@/lib/content";
import { formatDay } from "@/lib/news";
import { site } from "@/lib/site";
import "./globals.css";

const sans = Golos_Text({ variable: "--font-sans", subsets: ["latin", "cyrillic"] });
const serif = Literata({
  variable: "--font-serif",
  subsets: ["latin", "cyrillic"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  title: { default: site.name, template: `%s — ${site.name}` },
  description: site.description,
};

export default async function RootLayout({ children }: LayoutProps<"/">) {
  const [latest] = await getArticles();

  return (
    <html lang="ru" className={`${sans.variable} ${serif.variable}`}>
      <body>
        <a className="skip-link" href="#content">
          К содержанию
        </a>
        <Header today={formatDay(latest?.publishedAt ?? new Date().toISOString())} />
        <main id="content" className="page">
          {children}
        </main>
        <Footer />
      </body>
    </html>
  );
}
