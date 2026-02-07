const SUPABASE_URL = "PASTE_SUPABASE_PROJECT_URL_HERE";
const SUPABASE_ANON_KEY = "PASTE_SUPABASE_ANON_KEY_HERE";

const statusEl = document.getElementById("status");
const listEl = document.getElementById("list");
const topicEl = document.getElementById("topic");
const qEl = document.getElementById("q");
const reloadBtn = document.getElementById("reload");

function topicToBg(t) {
  return { politics:"Политика", world:"Световни", economy:"Икономика", sport:"Спорт", burgas:"Бургас" }[t] || t;
}

async function fetchApproved() {
  const topic = topicEl.value;
  const q = qEl.value.trim().toLowerCase();

  let url = new URL(`${SUPABASE_URL}/rest/v1/news_items`);
  url.searchParams.set("select", "source,topic,title_bg,title,url,published_at");
  url.searchParams.set("approved", "eq.true");
  url.searchParams.set("order", "published_at.desc");
  url.searchParams.set("limit", "80");

  if (topic !== "all") url.searchParams.set("topic", `eq.${topic}`);

  statusEl.textContent = "Зареждам…";

  const res = await fetch(url.toString(), {
    headers: {
      apikey: SUPABASE_ANON_KEY,
      Authorization: `Bearer ${SUPABASE_ANON_KEY}`,
    }
  });

  if (!res.ok) {
    statusEl.textContent = `Грешка при зареждане: ${res.status}`;
    return [];
  }

  let items = await res.json();

  if (q) {
    items = items.filter(x => (x.title_bg || x.title || "").toLowerCase().includes(q));
  }

  statusEl.textContent = `Показвам ${items.length} новини.`;
  return items;
}

function render(items) {
  listEl.innerHTML = "";
  for (const it of items) {
    const title = it.title_bg || it.title || "(без заглавие)";
    const dt = it.published_at ? new Date(it.published_at).toLocaleString("bg-BG") : "";
    const div = document.createElement("div");
    div.className = "item";
    div.innerHTML = `
      <div class="meta">
        <span class="badge">${topicToBg(it.topic)}</span>
        <span>${it.source || ""}</span>
        <span>${dt}</span>
      </div>
      <h3 style="margin:10px 0 0 0;">
        <a href="${it.url}" target="_blank" rel="noopener noreferrer">${title}</a>
      </h3>
    `;
    listEl.appendChild(div);
  }
}

async function load() {
  const items = await fetchApproved();
  render(items);
}

reloadBtn.addEventListener("click", load);
topicEl.addEventListener("change", load);
qEl.addEventListener("input", () => {
  // малко “debounce”
  clearTimeout(window.__t);
  window.__t = setTimeout(load, 250);
});

load();
