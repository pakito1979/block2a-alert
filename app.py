

import json
from pathlib import Path
import json
from datetime import datetime

CRONO_PATH = Path("cronograma.json")

def guardar_eventos_cronograma(eventos):
    if CRONO_PATH.exists():
        with open(CRONO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.extend(eventos)

    with open(CRONO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

from pathlib import Path
import streamlit as st
from pathlib import Path
import json
from pathlib import Path
import json
from datetime import datetime

CRONO_PATH = Path("cronograma.json")

def guardar_eventos_cronograma(eventos):
    if CRONO_PATH.exists():
        with open(CRONO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.extend(eventos)

    with open(CRONO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

from datetime import datetime
from pathlib import Path
import json
from datetime import datetime

CRONO_PATH = Path("cronograma.json")

def guardar_eventos_cronograma(eventos):
    if CRONO_PATH.exists():
        with open(CRONO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.extend(eventos)

    with open(CRONO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


CRONO_PATH = Path("cronograma.json")

def guardar_eventos_cronograma(eventos):
    if CRONO_PATH.exists():
        with open(CRONO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.extend(eventos)

    with open(CRONO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

import pandas as pd
from pathlib import Path
import json
from datetime import datetime

CRONO_PATH = Path("cronograma.json")

def guardar_eventos_cronograma(eventos):
    if CRONO_PATH.exists():
        with open(CRONO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.extend(eventos)

    with open(CRONO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

import plotly.express as px
from pathlib import Path
import json
from datetime import datetime

CRONO_PATH = Path("cronograma.json")

def guardar_eventos_cronograma(eventos):
    if CRONO_PATH.exists():
        with open(CRONO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.extend(eventos)

    with open(CRONO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)



from collector import run_collection, read_recent_events
from pathlib import Path
import json
from datetime import datetime

CRONO_PATH = Path("cronograma.json")

def guardar_eventos_cronograma(eventos):
    if CRONO_PATH.exists():
        with open(CRONO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.extend(eventos)

    with open(CRONO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

from analyzer import analyze_all_events
from pathlib import Path
import json
from datetime import datetime

CRONO_PATH = Path("cronograma.json")

def guardar_eventos_cronograma(eventos):
    if CRONO_PATH.exists():
        with open(CRONO_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = []

    data.extend(eventos)

    with open(CRONO_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

 


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
st.divider()

if st.button("Ejecutar búsqueda"):
    st.info("Búsqueda ejecutada (placeholder).")

if st.button("Analizar (importancia, categorías, catalizadores)"):
    resultados = analizar_todos_los_eventos()

    eventos_crono = []

    for r in resultados:
        eventos_crono.append({
            "empresa": r.get("company"),
            "evento": r.get("title"),
            "fecha": r.get("created_ts") or datetime.utcnow().isoformat(),
            "importancia": r.get("confidence", 1)
        })

    guardar_eventos_cronograma(eventos_crono)

    st.success(f"Análisis completado. {len(eventos_crono)} eventos añadidos al cronograma.")



   


with tab3:
    st.subheader("Diagnóstico base de datos (cronograma)")

    import sqlite3
    import pandas as pd

    con = sqlite3.connect("alertas.db")

    tablas = pd.read_sql_query(
        "SELECT name FROM sqlite_master WHERE type='table';",
        con
    )

    st.write("Tablas en la base de datos:")
    st.dataframe(tablas)

    if not tablas.empty:
        tabla = tablas.iloc[0]["name"]
        st.write(f"Ejemplo de datos de la tabla: {tabla}")

        ejemplo = pd.read_sql_query(
            f"SELECT * FROM {tabla} LIMIT 5",
            con
        )
        st.dataframe(ejemplo)

    con.close()

   
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
































































