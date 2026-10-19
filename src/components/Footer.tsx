import { getArticles, isDemo } from "@/lib/content";
import { site } from "@/lib/site";

export default async function Footer() {
  const credits = [...new Map(
    (await getArticles()).filter((a) => a.photo?.credit).map((a) => [a.photo!.src, a.photo!]),
  ).values()];

  return (
    <footer className="footer">
      <div className="footer-inner">
        <p className="footer-name">{site.name}</p>
        {isDemo && (
          <p className="footer-note">
            Демонстрационная версия: все материалы, имена и цифры вымышлены. Фотографии —
            иллюстрации из Wikimedia Commons и не относятся к событиям в текстах.
          </p>
        )}
        {credits.length > 0 && (
          <details className="footer-credits">
            <summary>Авторы фотографий</summary>
            <ul>
              {credits.map((photo) => (
                <li key={photo.src}>
                  {photo.page ? (
                    <a href={photo.page} target="_blank" rel="noreferrer">
                      {photo.credit}
                    </a>
                  ) : (
                    photo.credit
                  )}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>
    </footer>
  );
}
