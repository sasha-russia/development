// Dashboard: filters in the URL, heat map (yellow -> red), topic bars, problems, queue.
const form = document.getElementById("filters");
const state = new URLSearchParams(location.search);
if (!state.has("period")) state.set("period", "day");
if (!state.has("sentiment")) state.set("sentiment", "negative");

// Yellow at the least, red at the most. Nothing below yellow on the spectrum.
const GRADIENT = { 0.0: "#ffe14d", 0.35: "#ffc21a", 0.6: "#ff8c00", 0.8: "#f24b0f", 1.0: "#c40000" };
function heatColor(t) {
  const hue = 52 * (1 - Math.min(1, Math.max(0, t))); // 52 = yellow, 0 = red
  return `hsl(${hue}, 100%, ${50 - 8 * t}%)`;
}

const map = L.map("map", { zoomControl: true }).setView(window.CITY_CENTER, 12);
// OpenStreetMap tiles, desaturated in CSS so the yellow-red heat reads clearly.
L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
  maxZoom: 19, className: "base-tiles",
  attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">участники OpenStreetMap</a>',
}).addTo(map);
const heat = L.heatLayer([], { radius: 28, blur: 22, minOpacity: 0.45, gradient: GRADIENT }).addTo(map);
const places = L.layerGroup().addTo(map);
let fitted = false;

function syncControls() {
  form.querySelectorAll("[data-period]").forEach((b) => b.setAttribute("aria-pressed", b.dataset.period === state.get("period")));
  const topics = state.getAll("topic");
  form.querySelectorAll("[data-topic]").forEach((b) => b.setAttribute("aria-pressed", topics.includes(b.dataset.topic)));
  form.querySelector(".custom-range").hidden = state.get("period") !== "custom";
  for (const name of ["sentiment", "platform", "role"]) form.elements[name].value = state.get(name) || "";
  form.elements.from.value = state.get("from") || "";
  form.elements.to.value = state.get("to") || "";
}

function update() {
  history.replaceState(null, "", "?" + state.toString());
  syncControls();
  load();
}

form.addEventListener("click", (e) => {
  const p = e.target.closest("[data-period]");
  if (p) {
    state.set("period", p.dataset.period);
    if (p.dataset.period !== "custom") { state.delete("from"); state.delete("to"); update(); }
    else syncControls();
    return;
  }
  const t = e.target.closest("[data-topic]");
  if (t) {
    const topics = state.getAll("topic");
    state.delete("topic");
    const next = topics.includes(t.dataset.topic) ? topics.filter((x) => x !== t.dataset.topic) : [...topics, t.dataset.topic];
    next.forEach((x) => state.append("topic", x));
    update();
  }
});
document.getElementById("apply-range").addEventListener("click", () => {
  if (!form.elements.from.value) return;
  state.set("from", form.elements.from.value);
  form.elements.to.value ? state.set("to", form.elements.to.value) : state.delete("to");
  update();
});
form.addEventListener("change", (e) => {
  if (!["sentiment", "platform", "role"].includes(e.target.name)) return;
  e.target.value ? state.set(e.target.name, e.target.value) : state.delete(e.target.name);
  update();
});

async function load() {
  const res = await fetch("/api/dashboard?" + state.toString());
  if (res.status === 401) return (location.href = "/login");
  const data = await res.json();
  const s = data.stats;
  document.getElementById("k-total").textContent = s.total;
  document.getElementById("k-negative").textContent = s.negative;
  document.getElementById("k-problems").textContent = s.problems;
  document.getElementById("k-governor").textContent = s.governor;
  document.getElementById("period").textContent = data.period;

  const maxTopic = Math.max(1, ...s.topics.map((t) => t.total));
  document.getElementById("topics").innerHTML = s.topics.map((t) => `
    <button type="button" class="bar" data-topic-filter="${t.key}">
      <span class="bar-label">${esc(t.label)}</span>
      <span class="bar-track"><i style="width:${(100 * t.total) / maxTopic}%"></i><i class="neg" style="width:${(100 * t.negative) / maxTopic}%"></i></span>
      <span class="bar-num">${t.total}</span>
    </button>`).join("");

  document.getElementById("problems").innerHTML = data.problems.slice(0, 12).map((p) => `
    <li><a href="/problems/${p.id}"><b>${esc(p.title)}</b></a>
      <span class="muted">${esc(p.topic_label)} · ${p.mentions} упом. · ${p.comments} комм.${p.governor ? ` · <span class="gov-text">губернатор ${p.governor}</span>` : ""}</span></li>`).join("")
    || '<li class="muted">Нет проблем за период</li>';

  document.getElementById("queue").innerHTML = data.queue.map(itemCard).join("") || '<p class="muted">Очередь пуста</p>';

  drawMap(data.heat);
}

document.getElementById("topics").addEventListener("click", (e) => {
  const b = e.target.closest("[data-topic-filter]");
  if (!b) return;
  state.delete("topic");
  state.append("topic", b.dataset.topicFilter);
  update();
});

function drawMap(points) {
  const max = Math.max(1, ...points.map((p) => p.count));
  heat.setOptions({ max });
  heat.setLatLngs(points.map((p) => [p.lat, p.lon, p.count]));
  places.clearLayers();
  for (const p of points) {
    // Log scale: one message is yellow, the busiest place is red.
    const t = max > 1 ? Math.log(p.count) / Math.log(max) : 0.5;
    L.circleMarker([p.lat, p.lon], {
      radius: 5 + 9 * t, color: "#7a1a00", weight: 1, fillColor: heatColor(t), fillOpacity: 0.9,
    }).bindTooltip(`${p.count} сообщ. · ${esc(p.topic)}`).on("click", () => openPlace(p)).addTo(places);
  }
  const located = points.reduce((n, p) => n + p.count, 0);
  document.getElementById("map-note").textContent = points.length
    ? `На карте ${located} сообщений с адресом. Нажмите на точку, чтобы увидеть сообщения.`
    : "За период нет сообщений с адресом.";
  if (!fitted && points.length) {
    map.fitBounds(L.latLngBounds(points.map((p) => [p.lat, p.lon])).pad(0.2), { maxZoom: 14 });
    fitted = true;
  }
}

async function openPlace(p) {
  const params = new URLSearchParams(state);
  params.set("lat", p.lat);
  params.set("lon", p.lon);
  const items = await (await fetch("/api/items?" + params)).json();
  document.getElementById("place-title").textContent = `${p.count} сообщ. в этой точке`;
  const problems = p.problems.map((x) => `<a class="tag problem" href="/problems/${x.id}">${esc(x.title)}</a>`).join(" ");
  document.getElementById("place-items").innerHTML = (problems ? `<p>${problems}</p>` : "") + items.map(itemCard).join("");
  document.getElementById("place").showModal();
}

syncControls();
load();
setInterval(load, 120000);
