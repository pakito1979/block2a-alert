import json
import os
import sqlite3
import hashlib
from datetime import datetime
from urllib.parse import urljoin

import requests
import feedparser
from bs4 import BeautifulSoup

DB_PATH = "alerts.db"
COMPANIES_PATH = "companies.json"

def db_init():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            id TEXT PRIMARY KEY,
            ts TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            source_url TEXT NOT NULL,
            published TEXT,
            detected_ts TEXT NOT NULL
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

def mark_seen_and_store_event(con, item_id: str, company: str, title: str, link: str, source_url: str, published: str | None):
    cur = con.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute("INSERT OR IGNORE INTO seen (id, ts) VALUES (?, ?)", (item_id, now))
    cur.execute("""
        INSERT OR IGNORE INTO events (id, company, title, link, source_url, published, detected_ts)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (item_id, company, title, link, source_url, published or "", now))

    con.commit()

def keyword_match(title: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    t = title.lower()
    return any(k.lower() in t for k in keywords)

def fetch_rss(source_url: str):
    d = feedparser.parse(source_url)
    items = []
    for e in d.entries[:80]:
        title = (e.get("title") or "").strip()
        link = (e.get("link") or "").strip()
        published = (e.get("published") or e.get("updated") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "published": published})
    return items

def fetch_html(source_url: str):
    r = requests.get(source_url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items = []
    for a in soup.select("a"):
        txt = a.get_text(strip=True)
        href = a.get("href")
        if not href or not txt:
            continue
        if len(txt) < 25:
            continue
        link = urljoin(source_url, href)
        items.append({"title": txt, "link": link, "published": ""})

    return items[:80]

def load_config():
    if not os.path.exists(COMPANIES_PATH):
        return []
    with open(COMPANIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return []
    for c in data:
        c.setdefault("enabled", True)
        c.setdefault("sources", [])
    return data

def run_collection():
    con = db_init()
    companies = load_config()

    new_hits = []
    for c in companies:
        if not c.get("enabled", True):
            continue

        company_name = (c.get("name") or "").strip()
        if not company_name:
            continue

        for s in c.get("sources", []):
            stype = (s.get("type") or "rss").lower().strip()
            surl = (s.get("url") or "").strip()
            keywords = s.get("keywords", []) or []

            if not surl:
                continue

            if stype == "rss":
                items = fetch_rss(surl)
            elif stype == "html":
                items = fetch_html(surl)
            else:
                continue

            for it in items:
                title = it["title"]
                link = it["link"]
                published = it.get("published", "")

                if not keyword_match(title, keywords):
                    continue

                item_id = make_id(company_name, link, title)
                if already_seen(con, item_id):
                    continue

                mark_seen_and_store_event(con, item_id, company_name, title, link, surl, published)
                new_hits.append({
                    "company": company_name,
                    "title": title,
                    "link": link,
                    "source_url": surl,
                    "published": published
                })

    return new_hits

def read_recent_events(limit: int = 200):
    con = db_init()
    cur = con.cursor()
    cur.execute("""
        SELECT company, title, link, source_url, published, detected_ts
        FROM events
        ORDER BY detected_ts DESC
        LIMIT ?
    """, (limit,))
    return cur.fetchall()
import json
import os
import sqlite3
import hashlib
from datetime import datetime
from urllib.parse import urljoin

import requests
import feedparser
from bs4 import BeautifulSoup

DB_PATH = "alerts.db"
COMPANIES_PATH = "companies.json"

def db_init():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS seen (id TEXT PRIMARY KEY, ts TEXT NOT NULL)")
    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            source_url TEXT NOT NULL,
            published TEXT,
            detected_ts TEXT NOT NULL
        )
    """)
    con.commit()
    return con

def make_id(company: str, link: str, title: str) -> str:
    raw = f"{company}|{link}|{title}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()

def already_seen(con, item_id: str) -> bool:
    cur = con.cursor()
    cur.execute("SELECT 1 FROM seen WHERE id=?", (item_id,))
    return cur.fetchone() is not None

def store(con, item_id: str, company: str, title: str, link: str, source_url: str, published: str):
    cur = con.cursor()
    now = datetime.utcnow().isoformat()
    cur.execute("INSERT OR IGNORE INTO seen (id, ts) VALUES (?, ?)", (item_id, now))
    cur.execute("""
        INSERT OR IGNORE INTO events (id, company, title, link, source_url, published, detected_ts)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (item_id, company, title, link, source_url, published or "", now))
    con.commit()

def keyword_match(title: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    t = title.lower()
    return any(k.lower() in t for k in keywords)

def fetch_rss(url: str):
    d = feedparser.parse(url)
    out = []
    for e in d.entries[:80]:
        title = (e.get("title") or "").strip()
        link = (e.get("link") or "").strip()
        published = (e.get("published") or e.get("updated") or "").strip()
        if title and link:
            out.append({"title": title, "link": link, "published": published})
    return out

def fetch_html(url: str):
    r = requests.get(url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    out = []
    for a in soup.select("a"):
        txt = a.get_text(strip=True)
        href = a.get("href")
        if not href or not txt:
            continue
        if len(txt) < 25:
            continue
        out.append({"title": txt, "link": urljoin(url, href), "published": ""})
    return out[:80]

def load_companies():
    if not os.path.exists(COMPANIES_PATH):
        return []
    with open(COMPANIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return []
    for c in data:
        c.setdefault("enabled", True)
        c.setdefault("sources", [])
    return data

def run_collection():
    con = db_init()
    companies = load_companies()
    new_hits = []

    for c in companies:
        if not c.get("enabled", True):
            continue
        name = (c.get("name") or "").strip()
        if not name:
            continue

        for s in c.get("sources", []):
            stype = (s.get("type") or "rss").lower().strip()
            surl = (s.get("url") or "").strip()
            keywords = s.get("keywords", []) or []
            if not surl:
                continue

            items = fetch_rss(surl) if stype == "rss" else fetch_html(surl) if stype == "html" else []
            for it in items:
                if not keyword_match(it["title"], keywords):
                    continue
                item_id = make_id(name, it["link"], it["title"])
                if already_seen(con, item_id):
                    continue
                store(con, item_id, name, it["title"], it["link"], surl, it.get("published", ""))
                new_hits.append({"company": name, **it, "source_url": surl})

    return new_hits

def read_recent_events(limit: int = 200):
    con = db_init()
    cur = con.cursor()
    cur.execute("""
        SELECT company, title, link, source_url, published, detected_ts
        FROM events
        ORDER BY detected_ts DESC
        LIMIT ?
    """, (limit,))
    return cur.fetchall()

import json
import os
import sqlite3
import hashlib
from datetime import datetime
from urllib.parse import urljoin

import requests
import feedparser
from bs4 import BeautifulSoup

DB_PATH = "alerts.db"
COMPANIES_PATH = "companies.json"

def db_init():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS seen (
            id TEXT PRIMARY KEY,
            ts TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            company TEXT NOT NULL,
            title TEXT NOT NULL,
            link TEXT NOT NULL,
            source_url TEXT NOT NULL,
            published TEXT,
            detected_ts TEXT NOT NULL
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

def store_event(con, item_id: str, company: str, title: str, link: str, source_url: str, published: str | None):
    cur = con.cursor()
    now = datetime.utcnow().isoformat()

    cur.execute("INSERT OR IGNORE INTO seen (id, ts) VALUES (?, ?)", (item_id, now))
    cur.execute("""
        INSERT OR IGNORE INTO events (id, company, title, link, source_url, published, detected_ts)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (item_id, company, title, link, source_url, (published or ""), now))

    con.commit()

def keyword_match(title: str, keywords: list[str]) -> bool:
    if not keywords:
        return True
    t = title.lower()
    return any(k.lower() in t for k in keywords)

def fetch_rss(source_url: str):
    d = feedparser.parse(source_url)
    items = []
    for e in d.entries[:100]:
        title = (e.get("title") or "").strip()
        link = (e.get("link") or "").strip()
        published = (e.get("published") or e.get("updated") or "").strip()
        if title and link:
            items.append({"title": title, "link": link, "published": published})
    return items

def fetch_html(source_url: str):
    r = requests.get(source_url, timeout=25, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    items = []
    for a in soup.select("a"):
        txt = a.get_text(strip=True)
        href = a.get("href")
        if not href or not txt:
            continue

        # Filtro básico para evitar ruido de menús
        if len(txt) < 25:
            continue

        link = urljoin(source_url, href)
        items.append({"title": txt, "link": link, "published": ""})

    return items[:100]

def load_companies():
    if not os.path.exists(COMPANIES_PATH):
        return []
    with open(COMPANIES_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        return []
    for c in data:
        c.setdefault("enabled", True)
        c.setdefault("sources", [])
    return data

def run_collection():
    con = db_init()
    companies = load_companies()
    new_hits = []

    for c in companies:
        if not c.get("enabled", True):
            continue

        company_name = (c.get("name") or "").strip()
        if not company_name:
            continue

        for s in c.get("sources", []):
            stype = (s.get("type") or "rss").lower().strip()
            surl = (s.get("url") or "").strip()
            keywords = s.get("keywords", []) or []

            if not surl:
                continue

            if stype == "rss":
                items = fetch_rss(surl)
            elif stype == "html":
                items = fetch_html(surl)
            else:
                continue

            for it in items:
                title = it["title"]
                link = it["link"]
                published = it.get("published", "")

                if not keyword_match(title, keywords):
                    continue

                item_id = make_id(company_name, link, title)
                if already_seen(con, item_id):
                    continue

                store_event(con, item_id, company_name, title, link, surl, published)
                new_hits.append({
                    "id": item_id,
                    "company": company_name,
                    "title": title,
                    "link": link,
                    "source_url": surl,
                    "published": published
                })

    return new_hits

def read_recent_events(limit: int = 200):
    con = db_init()
    cur = con.cursor()
    cur.execute("""
        SELECT id, company, title, link, source_url, published, detected_ts
        FROM events
        ORDER BY detected_ts DESC
        LIMIT ?
    """, (limit,))
    return cur.fetchall()
