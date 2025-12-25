

import json
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px


from collector import run_collection, read_recent_events
from analyzer import analyze_all_events

 


COMPANIES_PATH = Path("companies.json")

def load_companies():
    if not COMPANIES_PATH.exists():
        return []
    try:
        return json.loads(COMPANIES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_companies(companies):
    COMPANIES_PATH.write_text(json.dumps(companies, indent=2, ensure_ascii=False), encoding="utf-8")

def ensure_format(companies):
    changed = False
    if not isinstance(companies, list):
        companies = []
        changed = True
    for c in companies:
        c.setdefault("enabled", True)
        if "sources" not in c:
            c["sources"] = []
            changed = True
    if changed:
        save_companies(companies)
    return companies

def db_connect():
    import sqlite3
    return sqlite3.connect("alerts.db")

st.set_page_config(page_title="Sistema de Alertas", layout="wide")
st.title("Sistema de Alertas: cronograma y catalizadores")

companies = ensure_format(load_companies())

tab1, tab2, tab3, tab4 = st.tabs(["Empresas", "Buscar", "Cronograma", "Catalizadores"])

with tab1:
    st.subheader("Empresas y fuentes")
    colA, colB = st.columns([1, 2])

    with colA:
        st.subheader("Lista")
        if companies:
            names = [c.get("name", "(sin nombre)") for c in companies]
            idx = st.selectbox("Selecciona", range(len(names)), format_func=lambda i: names[i])
            selected = companies[idx]
        else:
            idx = None
            selected = None
            st.info("Aún no hay empresas.")

        st.divider()
        st.subheader("Añadir empresa")
        with st.form("add_company"):
            new_name = st.text_input("Nombre")
            ok = st.form_submit_button("Crear")
            if ok:
                if not new_name.strip():
                    st.error("Pon un nombre.")
                else:
                    companies.append({"name": new_name.strip(), "enabled": True, "sources": []})
                    save_companies(companies)
                    st.success("Creada.")
                    st.rerun()

    with colB:
        if selected is None:
            st.warning("Crea una empresa para empezar.")
        else:
            st.markdown(f"**Empresa:** {selected.get('name','')}")
            selected["enabled"] = st.checkbox("Activa", value=selected.get("enabled", True))

            st.subheader("Fuentes")
            if selected["sources"]:
                for si, s in enumerate(selected["sources"]):
                    c1, c2, c3, c4 = st.columns([1, 4, 3, 1])
                    c1.write(s.get("type", "rss"))
                    c2.write(s.get("url", ""))
                    c3.write(", ".join(s.get("keywords", []) or []))
                    if c4.button("Borrar", key=f"del_{idx}_{si}"):
                        selected["sources"].pop(si)
                        companies[idx] = selected
                        save_companies(companies)
                        st.rerun()
            else:
                st.info("No hay fuentes. Añade una abajo.")

            st.divider()
            st.subheader("Añadir fuente")
            with st.form("add_source"):
                stype = st.selectbox("Tipo", ["rss", "html"])
                surl = st.text_input("URL")
                keywords = st.text_input("Keywords (opcional, separadas por comas)")
                ok2 = st.form_submit_button("Añadir")
                if ok2:
                    if not surl.strip():
                        st.error("Pon una URL.")
                    else:
                        selected["sources"].append({
                            "type": stype,
                            "url": surl.strip(),
                            "keywords": [k.strip() for k in keywords.split(",") if k.strip()]
                        })
                        companies[idx] = selected
                        save_companies(companies)
                        st.success("Fuente añadida.")
                        st.rerun()

            companies[idx] = selected
            save_companies(companies)

with tab2:
    st.subheader("Buscar noticias y analizar")
    st.write("Primero recoge noticias. Luego pulsa analizar para que aparezcan cronograma e importancia.")

    st.subheader("Cronograma de eventos")
    st.info("Cronograma cargado correctamente (versión inicial).")


   


with tab3:
    st.subheader("Cronograma (por meses) con importancia")
    analyze_hint = st.caption("Si esto sale vacío, ve a Buscar y pulsa Analizar.")
import pandas as pd
import plotly.express as px
import sqlite3

con = sqlite3.connect("alertas.db")

query = """
SELECT
    company,
    title,
    confidence,
    created_ts
FROM alerts
WHERE created_ts IS NOT NULL
ORDER BY created_ts ASC
"""

df = pd.read_sql_query(query, con)
con.close()

if df.empty:
    st.warning("No hay alertas todavía para mostrar en el cronograma.")
else:
    df["created_ts"] = pd.to_datetime(df["created_ts"])

    def importancia(conf):
        if conf >= 4:
            return "Alta"
        elif conf == 3:
            return "Media"
        else:
            return "Baja"

    df["Importancia"] = df["confidence"].apply(importancia)

    fig = px.timeline(
        df,
        x_start="created_ts",
        x_end="created_ts",
        y="title",
        color="Importancia",
        color_discrete_map={
            "Alta": "red",
            "Media": "orange",
            "Baja": "green"
        },
        hover_data=["company"]
    )

    fig.update_layout(
        height=600,
        xaxis_title="Fecha",
        yaxis_title="Evento"
    )

    st.plotly_chart(fig, use_container_width=True)

    con = db_connect()
    q = """
    SELECT e.company, e.title, e.link, e.published, e.detected_ts,
           a.category, a.importance, a.milestone_type
    FROM events e
    LEFT JOIN event_analysis a ON a.id = e.id
    ORDER BY e.detected_ts DESC
    """
    df = pd.read_sql_query(q, con)
    con.close()

    if df.empty:
        st.info("No hay eventos todavía.")
    else:
        companies_list = ["(Todas)"] + sorted(df["company"].dropna().unique().tolist())
        csel = st.selectbox("Empresa", companies_list)

        if csel != "(Todas)":
            df = df[df["company"] == csel]

        df["month"] = df["detected_ts"].astype(str).str.slice(0, 7)

        order = st.selectbox("Orden", ["Más recientes", "Mayor importancia"])
        if order == "Mayor importancia":
            df = df.sort_values(by=["importance", "detected_ts"], ascending=[False, False])

        months = sorted(df["month"].dropna().unique().tolist(), reverse=True)
        for m in months[:24]:
            st.markdown(f"### {m}")
            block = df[df["month"] == m].head(50)
            for _, r in block.iterrows():
                imp = int(r["importance"]) if str(r["importance"]).isdigit() else 0
                cat = r["category"] if pd.notna(r["category"]) else "No analizado"
                ms = r["milestone_type"] if pd.notna(r["milestone_type"]) else ""
                badge = "🔥" if imp >= 5 else "🟠" if imp == 4 else "🟡" if imp == 3 else "⚪"
                st.markdown(f"- {badge} **{r['company']}** [{r['title']}]({r['link']})  \n  {cat} | imp {imp}/5 | {ms}")

with tab4:
    st.subheader("Catalizadores probables")
    st.caption("Se generan con reglas simples a partir de titulares. Luego lo afinamos por empresa.")

    con = db_connect()
    q = """
    SELECT company, catalyst, expected_when, confidence, created_ts
    FROM catalysts
    ORDER BY created_ts DESC
    """
    dfc = pd.read_sql_query(q, con)
    con.close()

    if dfc.empty:
        st.info("No hay catalizadores todavía. Ve a Buscar y pulsa Analizar.")
    else:
        companies_list = ["(Todas)"] + sorted(dfc["company"].dropna().unique().tolist())
        csel = st.selectbox("Empresa (catalizadores)", companies_list, key="csel2")
        if csel != "(Todas)":
            dfc = dfc[dfc["company"] == csel]

        dfc = dfc.head(200)
        for _, r in dfc.iterrows():
            conf = int(r["confidence"]) if str(r["confidence"]).isdigit() else 1
            icon = "✅" if conf >= 4 else "🟡" if conf == 3 else "⚪"
            st.markdown(f"- {icon} **{r['company']}**: {r['catalyst']} | {r['expected_when']}")
         # cronograma añadido
































































