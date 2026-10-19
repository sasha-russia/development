import { notFound } from "next/navigation";
import Card from "@/components/Card";
import { byFormat } from "@/lib/content";
import { type Format, formats } from "@/lib/news";

function isFormat(value: string): value is Format {
  return value in formats;
}

export function generateStaticParams() {
  return Object.keys(formats).map((format) => ({ format }));
}

export async function generateMetadata({ params }: PageProps<"/rubric/[format]">) {
  const { format } = await params;
  return isFormat(format) ? { title: formats[format].plural } : {};
}

export default async function RubricPage({ params }: PageProps<"/rubric/[format]">) {
  const { format } = await params;
  if (!isFormat(format)) notFound();

  const items = await byFormat(format);

  return (
    <>
      <h1 className="rubric-title">{formats[format].plural}</h1>
      <div className="grid">
        {items.map((article) => (
          <Card key={article.slug} article={article} />
        ))}
      </div>
    </>
  );
}
