import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Resiban - Gestao de Producao",
    page_icon="♻️",
    layout="centered",
    initial_sidebar_state="expanded",
)

st.sidebar.markdown("## Resiban")
st.sidebar.markdown("**Gestao de Producao**")
st.sidebar.markdown("---")

pagina = st.sidebar.radio(
    "Menu",
    [
        "Dashboard",
        "OP Lavacao",
        "Producao Lavacao",
        "OP Extrusao",
        "Producao Extrusao",
        "Laboratorio",
        "Estoque",
        "Romaneio",
        "Exportar",
    ],
)

paginas_map = {
    "Dashboard": "pages/1_dashboard.py",
    "OP Lavacao": "pages/2_op_lavacao.py",
    "Producao Lavacao": "pages/3_producao_lavacao.py",
    "OP Extrusao": "pages/4_op_extrusao.py",
    "Producao Extrusao": "pages/5_producao_extrusao.py",
    "Laboratorio": "pages/6_qualidade.py",
    "Estoque": "pages/7_estoque.py",
    "Romaneio": "pages/8_romaneio.py",
    "Exportar": "pages/9_exportar.py",
}

with open(paginas_map[pagina], encoding="utf-8") as f:
    code = f.read()
exec(code)
