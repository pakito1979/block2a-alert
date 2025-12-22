import re
import sqlite3
from datetime import datetime

DB_PATH = "alerts.db"

CATEGORY_RULES = [
    ("M&A", ["acquisition", "acquire", "merger", "sale", "divest", "transaction", "deal", "purchase"]),
    ("Results", ["results", "earnings", "quarter", "q1", "q2", "q3", "q4", "annual", "interim"]),
    ("Guidance", ["guidance", "outlook", "forecast", "expects", "expected", "target", "update"]),
    ("Financing", ["credit facility", "refinanc", "debt", "notes", "bond", "equity", "financing", "loan", "liquidity"]),
    ("Operations", ["production", "well", "drill", "spud", "field", "operations", "lifting", "boe", "bbl", "gas"]),
    ("Dividends/Buybacks", ["dividend", "buyback", "repurchase", "distribution"]),
    ("Regulatory", ["approval", "permit", "license", "regulator", "sanction"]),
]

HIGH_IMPACT = ["acquisition", "merger", "sale", "divest", "credit facility", "refinanc", "dividend", "buyback"]
MID_IMPACT = ["results", "earnings", "guidance", "outlook", "production", "operations", "drill", "spud"]

QUARTER_RE = re.compile(r"\bQ([1-4])\b", re.IGNORECASE)
YEAR_RE = re.compile(r"\b(20\d{2})\b")

def db_init_analysis():
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS event_analysis (
            id TEXT PRIMARY KEY,
            category TEXT,
            importance INTEGER,
            summary TEXT,
            milestone_type TEXT,
            created_ts TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS catalysts (
            cid INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT,
            company TEXT,
            catalyst TEXT,
            expected_when TEXT,
            confidence INTEGER,
            created_ts TEXT NOT NULL
        )
    """)

    con.commit()
    return con

def classify_category(title: str) -> str:
    t = title.lower()
    for cat, kws in CATEGORY_RULES:
        if any(k in t for k in kws):
            return cat
    return "Other"

def score_importance(title: str, category: str) -> int:
    t = title.lower()
    score = 2

    # Base por categoría
    if category == "M&A":
        score = 5
    elif category in ["Financing", "Dividends/Buybacks"]:
        score = 4
    elif category in ["Results", "Guidance"]:
        score = 4
    elif category == "Operations":
        score = 3
    else:
        score = 2

    # Ajustes por keywords de impacto
    if any(k in t for k in HIGH_IMPACT):
        score = max(score, 4)
    if any(k in t for k in MID_IMPACT):
        score = max(score, 3)

    # Si hay año o trimestre, suele ser hito formal
    if YEAR_RE.search(title) or QUARTER_RE.search(title):
        score = min(5, score + 1)

    return max(1, min(5, score))

def milestone_type(title: str, category: str) -> str:
    t = title.lower()
    if any(k in t for k in ["announces", "launch", "commence", "to begin", "plans", "expects", "expected"]):
        return "Plan/Forward"
    if any(k in t for k in ["completed", "closed", "final", "achieves", "delivered"]):
        return "Completed"
    if category in ["Results", "Guidance"]:
        return "Report/Update"
    return "Update"

def build_summary(company: str, title: str, category: str, importance: int) -> str:
    return f"{company}: {category} (imp {importance}/5). {title}"

def extract_catalysts(company: str, title: str, category: str):
    t = title.lower()
    out = []

    # Reglas muy simples pero útiles
    if category in ["Results", "Guidance"]:
        q = QUARTER_RE.search(title)
        y = YEAR_RE.search(title)
        when = ""
        if q and y:
            when = f"Q{q.group(1)} {y.group(1)}"
        elif y:
            when = y.group(1)
        else:
            when = "Próximo periodo"
        out.append(("Update de resultados/guidance", when, 3))

    if any(k in t for k in ["expected", "expects", "to close", "closing"]):
        y = YEAR_RE.search(title)
        when = y.group(1) if y else "Próximo periodo"
        out.append(("Cierre o evento esperado", when, 3))

    if any(k in t for k in ["drill", "spud", "well"]):
        y = YEAR_RE.search(title)
        when = y.group(1) if y else "Próximo periodo"
        out.append(("Actividad de perforación/pozos", when, 2))

    if any(k in t for k in ["acquisition", "sale", "transaction", "deal"]):
        y = YEAR_RE.search(title)
        when = y.group(1) if y else "Próximo periodo"
        out.append(("Integración o cierre de transacción", when, 4))

    return out

def analyze_all_events():
    con = db_init_analysis()
    cur = con.cursor()

    cur.execute("""
        SELECT id, company, title
        FROM events
        ORDER BY detected_ts DESC
    """)
    rows = cur.fetchall()

    now = datetime.utcnow().isoformat()

    for (eid, company, title) in rows:
        # Si ya está analizado, no lo repetimos
        cur.execute("SELECT 1 FROM event_analysis WHERE id=?", (eid,))
        if cur.fetchone():
            continue

        cat = classify_category(title)
        imp = score_importance(title, cat)
        ms = milestone_type(title, cat)
        summ = build_summary(company, title, cat, imp)

        cur.execute("""
            INSERT OR IGNORE INTO event_analysis (id, category, importance, summary, milestone_type, created_ts)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (eid, cat, imp, summ, ms, now))

        cands = extract_catalysts(company, title, cat)
        for (catalyst, expected_when, conf) in cands:
            cur.execute("""
                INSERT INTO catalysts (event_id, company, catalyst, expected_when, confidence, created_ts)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (eid, company, catalyst, expected_when, conf, now))

    con.commit()
    con.close()
