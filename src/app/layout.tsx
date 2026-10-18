import type { Metadata } from "next";
import { PT_Serif, Inter } from "next/font/google";
import Header from "@/components/Header";
import "./globals.css";

const sans = Inter({ variable: "--font-sans", subsets: ["latin", "cyrillic"] });
const serif = PT_Serif({
  variable: "--font-serif",
  subsets: ["latin", "cyrillic"],
  weight: ["400", "700"],
});

export const metadata: Metadata = {
  title: "Development — новости",
  description: "Независимое новостное издание",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="ru" className={`${sans.variable} ${serif.variable}`}>
      <body>
        <Header />
        <main className="main">{children}</main>
      </body>
    </html>
  );
}
