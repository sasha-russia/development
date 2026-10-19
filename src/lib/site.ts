// Placeholder name until the publication has its own; change it here only.
export const site = {
  name: "Сводка",
  description: "Новости города: главное за день, истории, тесты и подкасты",
};

const basePath = process.env.NEXT_PUBLIC_BASE_PATH ?? "";

// Static files under public/ need the GitHub Pages basePath prepended.
export function asset(path: string) {
  return /^https?:\/\//.test(path) ? path : `${basePath}${path}`;
}
