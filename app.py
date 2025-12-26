import sys
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def _import_from_file(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise ImportError(f"No pude cargar el módulo desde: {file_path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    return mod


# 1) Preferimos aplicacion.py (sin tilde)
if (ROOT / "aplicacion.py").exists():
    _import_from_file("aplicacion", ROOT / "aplicacion.py")

# 2) Si no existe, probamos aplicación.py (con tilde)
elif (ROOT / "aplicación.py").exists():
    _import_from_file("aplicacion", ROOT / "aplicación.py")

# 3) Si no existe ninguno, mostramos error en la app
else:
    import streamlit as st
    st.error("No encuentro 'aplicacion.py' ni 'aplicación.py' en el repositorio.")

