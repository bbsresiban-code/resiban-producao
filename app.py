import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st

st.set_page_config(
    page_title="Resiban - Gestao de Producao",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "Painel": [
        st.Page("pages/1_dashboard.py", title="Dashboard", icon=":material/dashboard:"),
    ],
    "Lavacao": [
        st.Page("pages/2_op_lavacao.py", title="OP Lavacao", icon=":material/assignment:"),
        st.Page("pages/3_producao_lavacao.py", title="Producao Lavacao", icon=":material/local_laundry_service:"),
    ],
    "Extrusao": [
        st.Page("pages/4_op_extrusao.py", title="OP Extrusao", icon=":material/assignment:"),
        st.Page("pages/5_producao_extrusao.py", title="Producao Extrusao", icon=":material/precision_manufacturing:"),
    ],
    "Qualidade": [
        st.Page("pages/6_qualidade.py", title="Laboratorio", icon=":material/science:"),
        st.Page("pages/7_estoque.py", title="Estoque", icon=":material/inventory:"),
    ],
    "Logistica": [
        st.Page("pages/8_romaneio.py", title="Romaneio", icon=":material/local_shipping:"),
        st.Page("pages/9_exportar.py", title="Exportar", icon=":material/download:"),
    ],
}

nav = st.navigation(pages)

with st.sidebar:
    st.image("https://www.crbreciclagem.com.br/wp-content/uploads/2024/07/Logo-CRB-2024.webp", width=150)
    st.caption("Resiban - Gestao de Producao")

nav.run()
