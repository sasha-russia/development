import { articles } from "@/lib/news";
import { site } from "@/lib/site";

export default function Footer() {
  const credits = [...new Map(
    articles.filter((a) => a.photo).map((a) => [a.photo!.src, a.photo!]),
  ).values()];

  return (
    <footer className="footer">
      <div className="footer-inner">
        <p className="footer-name">{site.name}</p>
        <p className="footer-note">
          Демонстрационная версия: все материалы, имена и цифры вымышлены. Фотографии —
          иллюстрации из Wikimedia Commons и не относятся к событиям в текстах.
        </p>
        <details className="footer-credits">
          <summary>Авторы фотографий</summary>
          <ul>
            {credits.map((photo) => (
              <li key={photo.src}>
                <a href={photo.page} target="_blank" rel="noreferrer">
                  {photo.credit}
                </a>
              </li>
            ))}
          </ul>
        </details>
      </div>
    </footer>
  );
}
