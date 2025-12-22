import re
import sqlite3
import hashlib
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timezone

import requests
import feedparser
from bs4 import BeautifulSoup

SOURCES = [
    {"name": "INPEX IR RSS", "type": "rss", "url": "https://www.inpex.com/english/news/ir_rss.xml"},
    {"name": "INPEX News", "type": "html_news", "url": "https://www.inpex.com/english/news/"},
    {"name": "Seascape Ops Malaysia", "type": "html_generic", "url": "https://seascape-energy.com/operations-malaysia/"},
    {"name": "PETRONAS Media Releases", "type": "html_generic", "url": "https://www.petronas.com/media/media-releases"},
]

# Palabras clave que disparan alertas
MUST_MATCH = [r"inpex"
   
]

DB_PATH = "alerts.sqlite"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587

# RELLENA ESTO
SMTP_USER = "fcoaldea@gmail.com"
SMTP_PASS = "hwsz sqqc jyav squw"
EMAIL_TO = ["fcoaldea@gmail.com"]

HEADERS = {"User-Agent": "block2a-alert/1.0"}

def init_db():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            id TEXT PRIMARY KEY,
            first_seen_utc TEXT
        )
    """)
    con.commit()
    return con

def make_id(title: str, url: str, published: str) -> str:
    s = f"{title}\n{url}\n{published}".encode("utf-8", errors="ignore")
    return hashlib.sha256(s).hexdigest()

def already_seen(con, item_id: str) -> bool:
    cur = con.cursor()
    cur.execute("SELECT 1 FROM seen WHERE id=?", (item_id,))
    return cur.fetchone() is not None

def mark_seen(con, item_id: str):
    cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO seen (id, first_seen_utc) VALUES (?, ?)",
                (item_id, datetime.now(timezone.utc).isoformat()))
    con.commit()

def matches(text: str) -> bool:
    t = text.lower()
    return any(re.search(p, t, re.I) for p in MUST_MATCH)

def fetch_rss(url: str):
    feed = feedparser.parse(url)
    items = []
    for e in feed.entries:
        title = getattr(e, "title", "").strip()
        link = getattr(e, "link", "").strip()
        published = getattr(e, "published", "") or getattr(e, "updated", "")
        summary = getattr(e, "summary", "")
        items.append({"title": title, "url": link, "published": published, "text": f"{title}\n{summary}\n{link}"})
    return items

def fetch_inpex_news_listing(url: str):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    items = []

    for a in soup.select("a[href]"):
        href = a["href"]
        text = a.get_text(" ", strip=True)
        if href and (href.endswith(".pdf") or "assets/pdf" in href):
            full = href if href.startswith("http") else "https://www.inpex.com" + href
            items.append({"title": text or "INPEX News PDF", "url": full, "published": "", "text": f"{text}\n{full}"})

    items.append({"title": "INPEX News listing", "url": url, "published": "", "text": soup.get_text(" ", strip=True)[:2000]})
    return items

def fetch_html_generic(url: str):
    r = requests.get(url, headers=HEADERS, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    title = (soup.title.get_text(strip=True) if soup.title else url)
    text = soup.get_text(" ", strip=True)
    return [{"title": title, "url": url, "published": "", "text": f"{title}\n{text[:4000]}"}]

def send_email(subject: str, body: str):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ", ".join(EMAIL_TO)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as s:
        s.ehlo()
        s.starttls()
        s.ehlo()
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SMTP_USER, EMAIL_TO, msg.as_string())

def run_once(con):
    hits = []

    for src in SOURCES:
        try:
            if src["type"] == "rss":
                items = fetch_rss(src["url"])
            elif src["type"] == "html_news":
                items = fetch_inpex_news_listing(src["url"])
            else:
                items = fetch_html_generic(src["url"])
        except Exception as e:
            print(f"ERROR leyendo fuente: {src['name']} -> {e}")
            continue

        for it in items:
            item_id = make_id(it["title"], it["url"], it["published"])
            if already_seen(con, item_id):
                continue

            if matches(it["text"]):
                hits.append((src["name"], it))
                mark_seen(con, item_id)

    if hits:
        lines = []
        for src_name, it in hits:
            lines.append(f"[{src_name}] {it['title']}")
            lines.append(it["url"])
            if it["published"]:
                lines.append(f"Published: {it['published']}")
            lines.append("")
        body = "\n".join(lines)
        send_email("INPEX / Block 2A Alert", body)
        print("OK: email enviado (si había coincidencias)")
    else:
        print("OK: no hubo coincidencias, no se envió email")

if __name__ == "__main__":
    con = init_db()
    run_once(con)
