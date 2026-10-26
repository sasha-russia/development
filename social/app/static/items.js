// Message cards with status buttons, shared by the dashboard and the queue.
const STATUS = { new: "Новое", in_work: "В работе", done: "Отработано", ignored: "Не требует" };
const SENT = { negative: "негатив", neutral: "нейтрально", positive: "позитив" };
const KIND = { post: "пост", comment: "комментарий", chat: "чат" };

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function itemCard(i) {
  const prio = i.role === "governor" ? '<span class="tag gov">губернатор</span>' : i.priority === 2 ? '<span class="tag hi">важно</span>' : "";
  const parent = i.parent ? `<blockquote class="parent">к посту: ${esc(i.parent.slice(0, 220))}</blockquote>` : "";
  const problem = i.problem_id ? `<a class="tag problem" href="/problems/${i.problem_id}">${esc(i.problem)}</a>` : "";
  const buttons = Object.entries(STATUS).map(([k, v]) =>
    `<button type="button" data-status="${k}" ${i.status === k ? 'aria-pressed="true"' : ""}>${v}</button>`).join("");
  return `<article class="item s-${i.sentiment} p${i.priority}" data-id="${i.id}">
    <header>${prio}<span class="tag">${esc(i.topic_label)}</span><span class="tag ${i.sentiment}">${SENT[i.sentiment]}</span>
      <span class="meta">${esc(i.published)} · ${KIND[i.kind]} · <a href="${esc(i.url)}" target="_blank" rel="noopener">${esc(i.source)}</a>${i.author ? " · " + esc(i.author) : ""}</span></header>
    ${parent}<p class="text">${esc(i.text)}</p>
    <footer>${problem}${i.address ? `<span class="addr">📍 ${esc(i.address)}</span>` : ""}
      <span class="status-buttons">${buttons}</span></footer>
  </article>`;
}

document.addEventListener("click", async (e) => {
  const btn = e.target.closest(".status-buttons button");
  if (!btn) return;
  const card = btn.closest(".item");
  const res = await fetch(`/api/items/${card.dataset.id}/status`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: btn.dataset.status }),
  });
  if (!res.ok) return alert("Не удалось сохранить статус");
  card.querySelectorAll(".status-buttons button").forEach((b) => b.removeAttribute("aria-pressed"));
  btn.setAttribute("aria-pressed", "true");
  card.classList.add("updated");
});
