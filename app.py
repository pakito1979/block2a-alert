import sys
import streamlit as st
from pathlib import Path
import importlib.util

def load_module_from_file(file_path: Path, module_name: str = "aplicacion"):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

candidates = [Path("aplicacion.py"), Path("aplicación.py")]

for p in candidates:
    if p.exists():
        load_module_from_file(p, "aplicacion")
        st.stop()

st.error("No encuentro 'aplicacion.py' ni 'aplicación.py' en el repositorio.")
st.stop()
