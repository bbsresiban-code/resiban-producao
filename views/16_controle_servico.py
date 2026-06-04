import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date

from utils.database import read_sheet
from utils.formatters import formatar_peso, formatar_data

st.header("Controle de Servico (Industrializacao para Terceiros)")
st.caption("Materiais de Servico NAO entram no inventario proprio. Sao controlados aqui separadamente.")

try:
    df_aparas = read_sheet("aparas_estoque")
except Exception:
    df_aparas = pd.DataFrame()

try:
    df_ext = read_sheet("producao_extrusao")
except Exception:
    df_ext = pd.DataFrame()

try:
    df_op_ext = read_sheet("op_extrusao")
except Exception:
    df_op_ext = pd.DataFrame()

# ===========================================================================
# Filtrar so SERVICO
# ===========================================================================
if not df_aparas.empty and "tipo_material" in df_aparas.columns:
    df_aparas_serv = df_aparas[df_aparas["tipo_material"].astype(str) == "Servico"].copy()
else:
    df_aparas_serv = pd.DataFrame()

if not df_ext.empty and "tipo" in df_ext.columns:
    df_grao_serv = df_ext[df_ext["tipo"].astype(str) == "02"].copy()
else:
    df_grao_serv = pd.DataFrame()

if not df_op_ext.empty and "origem" in df_op_ext.columns:
    df_ope_serv = df_op_ext[df_op_ext["origem"].astype(str) == "Servico"].copy()
else:
    df_ope_serv = pd.DataFrame()

# ===========================================================================
# Metricas gerais
# ===========================================================================
peso_apa_aguard = 0.0
peso_apa_disp = 0.0
peso_apa_uso = 0.0
qtd_apa_aguard = 0
qtd_apa_disp = 0
qtd_apa_uso = 0
if not df_aparas_serv.empty:
    df_aparas_serv["peso_kg"] = pd.to_numeric(df_aparas_serv["peso_kg"], errors="coerce").fillna(0)
    peso_apa_aguard = float(df_aparas_serv[df_aparas_serv["status"] == "aguardando_classificacao"]["peso_kg"].sum())
    peso_apa_disp = float(df_aparas_serv[df_aparas_serv["status"] == "disponivel"]["peso_kg"].sum())
    peso_apa_uso = float(df_aparas_serv[df_aparas_serv["status"] == "em_uso"]["peso_kg"].sum())
    qtd_apa_aguard = len(df_aparas_serv[df_aparas_serv["status"] == "aguardando_classificacao"])
    qtd_apa_disp = len(df_aparas_serv[df_aparas_serv["status"] == "disponivel"])
    qtd_apa_uso = len(df_aparas_serv[df_aparas_serv["status"] == "em_uso"])

peso_grao_analise = 0.0
peso_grao_disp = 0.0
qtd_grao_analise = 0
qtd_grao_disp = 0
if not df_grao_serv.empty:
    df_grao_serv["peso_kg"] = pd.to_numeric(df_grao_serv["peso_kg"], errors="coerce").fillna(0)
    peso_grao_analise = float(df_grao_serv[df_grao_serv["status"] == "em_analise"]["peso_kg"].sum())
    peso_grao_disp = float(df_grao_serv[df_grao_serv["status"] == "disponivel"]["peso_kg"].sum())
    qtd_grao_analise = len(df_grao_serv[df_grao_serv["status"] == "em_analise"])
    qtd_grao_disp = len(df_grao_serv[df_grao_serv["status"] == "disponivel"])

# ===========================================================================
# Tabs
# ===========================================================================
tab_aparas, tab_grao, tab_ope = st.tabs(["Aparas de Servico", "Grao de Servico", "OPEs de Servico"])

with tab_aparas:
    st.subheader("Aparas de Servico (Terceiros)")
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    col_a1.metric("Aguardando Classif.", f"{qtd_apa_aguard} NF(s)", formatar_peso(peso_apa_aguard))
    col_a2.metric("Disponivel", f"{qtd_apa_disp} NF(s)", formatar_peso(peso_apa_disp))
    col_a3.metric("Em uso (OPE)", f"{qtd_apa_uso} NF(s)", formatar_peso(peso_apa_uso))
    col_a4.metric("**Total**", f"{qtd_apa_aguard + qtd_apa_disp + qtd_apa_uso} NF(s)",
                  formatar_peso(peso_apa_aguard + peso_apa_disp + peso_apa_uso))

    if df_aparas_serv.empty:
        st.info("Nenhuma apara de servico registrada.")
    else:
        cols = [c for c in ["numero_nf", "fornecedor", "qualidade", "tipo_fardo",
                            "quantidade", "peso_kg", "status", "opl_em_uso",
                            "data_recebimento", "data_classificacao"] if c in df_aparas_serv.columns]
        st.dataframe(df_aparas_serv[cols], use_container_width=True, hide_index=True)

with tab_grao:
    st.subheader("Grao de Servico (Tipo 02)")
    col_g1, col_g2, col_g3 = st.columns(3)
    col_g1.metric("Em Analise (Lab)", f"{qtd_grao_analise} lote(s)", formatar_peso(peso_grao_analise))
    col_g2.metric("Disponivel", f"{qtd_grao_disp} lote(s)", formatar_peso(peso_grao_disp))
    col_g3.metric("**Total**", f"{qtd_grao_analise + qtd_grao_disp} lote(s)",
                  formatar_peso(peso_grao_analise + peso_grao_disp))

    if df_grao_serv.empty:
        st.info("Nenhum grao de servico produzido.")
    else:
        cols = [c for c in ["codigo_lote", "data", "tipo_descricao", "extrusora",
                            "peso_kg", "status", "numero_op"] if c in df_grao_serv.columns]
        st.dataframe(df_grao_serv[cols], use_container_width=True, hide_index=True)

with tab_ope:
    st.subheader("OPEs de Servico")
    if df_ope_serv.empty:
        st.info("Nenhuma OPE de servico criada.")
    else:
        cols = [c for c in ["numero_op", "data", "cliente", "responsavel",
                            "volume_ton", "produto", "maquina", "status"] if c in df_ope_serv.columns]
        st.dataframe(df_ope_serv[cols], use_container_width=True, hide_index=True)
