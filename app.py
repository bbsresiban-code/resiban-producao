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

USUARIOS = {
    "master":     {"senha": st.secrets["senhas"]["master"],     "perfil": "master"},
    "turno_a":    {"senha": st.secrets["senhas"]["turno_a"],    "perfil": "turno"},
    "turno_b":    {"senha": st.secrets["senhas"]["turno_b"],    "perfil": "turno"},
    "turno_c":    {"senha": st.secrets["senhas"]["turno_c"],    "perfil": "turno"},
    "logistica":  {"senha": st.secrets["senhas"]["logistica"],  "perfil": "logistica"},
    "qualidade":  {"senha": st.secrets["senhas"]["qualidade"],  "perfil": "qualidade"},
}

PAGINAS_POR_PERFIL = {
    "master": [
        "Dashboard",
        "Recebimento MP",
        "Classificacao MP",
        "Estoque Aparas",
        "OP Lavacao",
        "Producao Lavacao",
        "OP Extrusao",
        "Producao Extrusao",
        "Mistura",
        "Laboratorio",
        "Estoque Resina",
        "Romaneio",
        "Laudos",
        "Exportar",
    ],
    "turno": [
        "Producao Lavacao",
        "Producao Extrusao",
    ],
    "logistica": [
        "Recebimento MP",
        "Estoque Aparas",
        "Laboratorio",
        "Estoque Resina",
        "Romaneio",
        "Laudos",
        "Exportar",
    ],
    "qualidade": [
        "Classificacao MP",
        "Estoque Aparas",
        "Laboratorio",
        "Estoque Resina",
        "Romaneio",
        "Laudos",
        "Exportar",
    ],
}

PAGINAS_MAP = {
    "Dashboard": "views/1_dashboard.py",
    "Recebimento MP": "views/12_recebimento_mp.py",
    "Classificacao MP": "views/13_classificacao_mp.py",
    "Estoque Aparas": "views/14_estoque_aparas.py",
    "OP Lavacao": "views/2_op_lavacao.py",
    "Producao Lavacao": "views/3_producao_lavacao.py",
    "OP Extrusao": "views/4_op_extrusao.py",
    "Producao Extrusao": "views/5_producao_extrusao.py",
    "Laboratorio": "views/6_qualidade.py",
    "Estoque Resina": "views/7_estoque.py",
    "Mistura": "views/11_mistura.py",
    "Romaneio": "views/8_romaneio.py",
    "Laudos": "views/10_laudos.py",
    "Exportar": "views/9_exportar.py",
}

if "logado" not in st.session_state:
    st.session_state.logado = False
    st.session_state.usuario = None
    st.session_state.perfil = None


def fazer_login(usuario, senha):
    if usuario in USUARIOS and USUARIOS[usuario]["senha"] == senha:
        st.session_state.logado = True
        st.session_state.usuario = usuario
        st.session_state.perfil = USUARIOS[usuario]["perfil"]
        return True
    return False


def fazer_logout():
    st.session_state.logado = False
    st.session_state.usuario = None
    st.session_state.perfil = None


LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "logo.png")

if not st.session_state.logado:
    col_logo, col_title = st.columns([1, 2])
    with col_logo:
        if os.path.exists(LOGO_PATH):
            st.image(LOGO_PATH, width=180)
    with col_title:
        st.markdown("## Resiban")
        st.markdown("**Sistema de Gestao de Producao**")
    st.markdown("---")

    with st.form("login"):
        usuario = st.selectbox(
            "Usuario",
            ["master", "turno_a", "turno_b", "turno_c", "logistica", "qualidade"],
        )
        senha = st.text_input("Senha", type="password")
        entrar = st.form_submit_button("Entrar")

    if entrar:
        if fazer_login(usuario, senha):
            st.rerun()
        else:
            st.error("Senha incorreta.")

else:
    perfil = st.session_state.perfil
    paginas_disponiveis = PAGINAS_POR_PERFIL[perfil]

    nomes_perfil = {
        "master": "Master",
        "turno": f"Turno {st.session_state.usuario[-1].upper()}",
        "logistica": "Logistica",
        "qualidade": "Qualidade",
    }

    if os.path.exists(LOGO_PATH):
        st.sidebar.image(LOGO_PATH, width=150)
    st.sidebar.markdown(f"**{nomes_perfil[perfil]}**")
    st.sidebar.markdown("---")

    pagina = st.sidebar.radio("Menu", paginas_disponiveis)

    st.sidebar.markdown("---")
    if st.sidebar.button("Sair"):
        fazer_logout()
        st.rerun()

    with open(PAGINAS_MAP[pagina], encoding="utf-8") as f:
        code = f.read()
    exec(code)
