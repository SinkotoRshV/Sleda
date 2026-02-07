import os, re
import requests
import feedparser
from dateutil import parser as dtparser

SUPABASE_URL = os.environ["SUPABASE_URL"].rstrip("/")
SERVICE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]

DEEPL_KEY = os.environ.get("DEEPL_API_KEY", "").strip()

# Старт: български източници (няма превод нужен).
# RSS-и:
# - BTA: https://www.bta.bg/bg/rss/free  (примерен публичен RSS) :contentReference[oaicite:0]{index=0}
# - Dnevnik: http://www.dnevnik.bg/rss/ :contentReference[oaicite:1]{index=1}
# - Capital: https://www2.capital.bg/rss.php :contentReference[oaicite:2]{index=2}
# - OFFNews: http://offnews.bg/rss/all :contentReference[oaicite:3]{index=3}
# - Burgas24: отваряш https://www.burgas24.bg/novini/rss.html и копираш реалния RSS линк :contentReference[oaicite:4]{index=4}

SOURCES = [
    {"name": "БТА", "topic": "world", "url": "https://www.bta.bg/bg/rss/free"},
    {"name": "Дневник", "topic": "politics", "url": "http://www.dnevnik.bg/rss/"},
    {"name": "Капитал", "topic": "economy", "url": "https://www2.capital.bg/rss.php"},
    {"name": "OFFNews", "topic": "politics", "url": "http://offnews.bg/rss/all"},

    # TODO: постави реален RSS за Бургас (взима се от страницата на Burgas24)
    # {"name": "Burgas24", "topic": "burgas", "url": "PASTE_BURGAS24_RSS_HERE"},
]

def looks_bg(text: str) -> bool:
    # грубо: кирилица => най-често BG (за MVP е ок)
    return bool(re.search(r"[А-Яа-я]", text or ""))

def deepl_translate_bg(text: str) -> str | None:
    if not DEEPL_KEY:
        return None

    endpoint = "https://api.deepl.com/v2/translate"
    # DeepL free ключовете често завършват на :fx
    if DEEPL_KEY.endswith(":fx"):
        endpoint = "https://api-free.deepl.com/v2/translate"

    r = requests.post(endpoint, data={
        "auth_key": DEEPL_KEY,
        "text": text,
        "target_lang": "BG"
    }, timeout=30)

    if r.status_code != 200:
        print("DeepL error:", r.status_code, r.text[:200])
        return None

    data = r.json()
    return data["translations"][0]["text"]

def supabase_upsert(item: dict):
    url = f"{SUPABASE_URL}/rest/v1/news_items?on_conflict=url"
    headers = {
        "apikey": SERVICE_KEY,
        "Authorization": f"Bearer {SERVICE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates",
    }
    r = requests.post(url, headers=headers, json=item, timeout=30)
    if r.status_code not in (200, 201, 204):
        # ако е дубликат, може да върне 409 при някои настройки – не е страшно
        if r.status_code == 409:
            return
        print("Supabase error:", r.status_code, r.text[:200])

def normalize_published(entry):
    for k in ("published", "updated", "created"):
        if k in entry and entry[k]:
            try:
                return dtparser.parse(entry[k]).isoformat()
            except Exception:
                pass
    return None

def run():
    for s in SOURCES:
        if "PASTE_" in s["url"]:
            continue

        feed = feedparser.parse(s["url"])
        for e in feed.entries[:50]:
            title = (e.get("title") or "").strip()
            link = (e.get("link") or "").strip()
            if not title or not link:
                continue

            published_at = normalize_published(e)

            title_bg = title
            lang = "bg" if looks_bg(title) else "other"

            # Ако НЕ е на български:
            # - ако имаме DeepL ключ => превеждаме
            # - ако нямаме => НЕ го записваме (за да е 100% български сайтът)
            if lang != "bg":
                tr = deepl_translate_bg(title)
                if not tr:
                    continue
                title_bg = tr
                lang = "translated"

            item = {
                "source": s["name"],
                "topic": s["topic"],
                "title": title,
                "title_bg": title_bg,
                "url": link,
                "published_at": published_at,
                "lang": lang,
                "approved": False,
            }
            supabase_upsert(item)

if __name__ == "__main__":
    run()
    print("Done.")
