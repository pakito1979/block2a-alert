import json
import sqlite3
import hashlib
from datetime import datetime
import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin

DB_PATH = "seen.db"
COMPANIES_PATH = "companies.json"

def db_init():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            link TEXT NOT NULL,
            title TEXT NOT NULL,
            ts TEXT NOT NULL
        )
    """)
    con.commit()
    return con

def make_id(company: str, link: str, title: str) -> str:
    raw = f"{company}|{link}|{title}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()

def already_seen(con, item_id: str) -> bool:
    cur = con.cursor()
    cur.execute("SELECT 1 FROM seen WHERE id = ?", (item_id,))
    return cur.fetchone() is not None

def mark_seen(con, item_id: str, company: str, link: str, title: str):
    cur = con.cursor()
    cur.execute(
        "INSERT OR IGNORE INTO seen (id, company, link, title, ts) VALUES (?, ?, ?, ?, ?)",
        (item_id, company, link, title, datetime.utcnow().isoformat())
    )
    con.commit()

def fetch_rss(company):
    d = feedparser.parse(company["url"])
    items = []
    for e in d.entries[:50]:
        title = (e.get("title") or "").strip()
        link = (e.get("link") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "date": e.get("published", "")})
    return items

def fetch_html(company):
    r = requests.get(company["url"], timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items = []
    base = company["url"]

    # Extracción genérica de enlaces (para HTML hay que afinar por web)
    for a in soup.select("a"):
        txt = a.get_text(strip=True)
        href = a.get("href")
        if not href or not txt:
            continue
        if len(txt) >= 25:
            link = urljoin(base, href)
            items.append({"title": txt, "link": link, "date": ""})

    return items[:50]

def keyword_match(title: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    t = title.lower()
    return any(k.lower() in t for k in keywords)

def load_companies():
    with open(COMPANIES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def check_all():
    con = db_init()
    companies = load_companies()

    new_hits = []
    for c in companies:
        if not c.get("enabled", True):
            continue

        ctype = (c.get("type") or "rss").lower()
        if ctype == "rss":
            items = fetch_rss(c)
        elif ctype == "html":
            items = fetch_html(c)
        else:
            print(f"[WARN] Tipo no soportado: {ctype} en {c.get('name')}")
            continue

        for it in items:
            if not keyword_match(it["title"], c.get("keywords", [])):
                continue

            item_id = make_id(c["name"], it["link"], it["title"])
            if already_seen(con, item_id):
                continue

            mark_seen(con, item_id, c["name"], it["link"], it["title"])
            new_hits.append({"company": c["name"], **it})

    return new_hits

if __name__ == "__main__":
    hits = check_all()
    if not hits:
        print("Sin novedades.")
    else:
        print(f"Novedades: {len(hits)}")
        for h in hits[:30]:
            print(f"- [{h['company']}] {h['title']} -> {h['link']}")
