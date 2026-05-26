import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import date, timedelta
from utils.database import read_sheet
from utils.formatters import formatar_peso, formatar_percentual

st.title("Dashboard de Producao")

col_f1, col_f2 = st.columns(2)
with col_f1:
    data_inicio = st.date_input("De", value=date.today().replace(day=1))
with col_f2:
    data_fim = st.date_input("Ate", value=date.today())

try:
    df_lavacao = read_sheet("producao_lavacao")
    df_extrusao = read_sheet("producao_extrusao")
    df_qualidade = read_sheet("qualidade")
    df_paradas = read_sheet("paradas_lavacao")
    df_romaneio = read_sheet("romaneio")
except Exception as e:
    st.error(f"Erro ao carregar dados: {e}")
    st.info("Configure a conexao com o Google Sheets em .streamlit/secrets.toml")
    st.stop()

for df in [df_lavacao, df_extrusao, df_qualidade, df_paradas, df_romaneio]:
    if not df.empty and "data" in df.columns:
        df["data"] = pd.to_datetime(df["data"], errors="coerce")

if not df_lavacao.empty:
    mask_lav = (df_lavacao["data"] >= pd.Timestamp(data_inicio)) & (df_lavacao["data"] <= pd.Timestamp(data_fim))
    df_lav_periodo = df_lavacao[mask_lav]
else:
    df_lav_periodo = pd.DataFrame()

if not df_extrusao.empty:
    mask_ext = (df_extrusao["data"] >= pd.Timestamp(data_inicio)) & (df_extrusao["data"] <= pd.Timestamp(data_fim))
    df_ext_periodo = df_extrusao[mask_ext]
else:
    df_ext_periodo = pd.DataFrame()

if not df_paradas.empty:
    mask_par = (df_paradas["data"] >= pd.Timestamp(data_inicio)) & (df_paradas["data"] <= pd.Timestamp(data_fim))
    df_par_periodo = df_paradas[mask_par]
else:
    df_par_periodo = pd.DataFrame()

st.markdown("---")

c1, c2, c3, c4, c5 = st.columns(5)

total_fardos_kg = 0
if not df_lav_periodo.empty and "peso_kg" in df_lav_periodo.columns:
    df_lav_periodo["peso_kg"] = pd.to_numeric(df_lav_periodo["peso_kg"], errors="coerce")
    total_fardos_kg = df_lav_periodo["peso_kg"].sum()
c1.metric("Fardos Processados", formatar_peso(total_fardos_kg))

total_bags = 0
total_bags_kg = 0
if not df_ext_periodo.empty and "peso_kg" in df_ext_periodo.columns:
    df_ext_periodo["peso_kg"] = pd.to_numeric(df_ext_periodo["peso_kg"], errors="coerce")
    total_bags = len(df_ext_periodo)
    total_bags_kg = df_ext_periodo["peso_kg"].sum()
c2.metric("Bigbags Produzidos", f"{total_bags} ({formatar_peso(total_bags_kg)})")

lotes_analise = 0
if not df_extrusao.empty and "status" in df_extrusao.columns:
    lotes_analise = len(df_extrusao[df_extrusao["status"] == "em_analise"])
c3.metric("Em Analise", f"{lotes_analise} lotes")

lotes_disponiveis = 0
kg_disponiveis = 0
if not df_extrusao.empty and "status" in df_extrusao.columns:
    disp = df_extrusao[df_extrusao["status"] == "disponivel"]
    lotes_disponiveis = len(disp)
    if "peso_kg" in disp.columns:
        disp["peso_kg"] = pd.to_numeric(disp["peso_kg"], errors="coerce")
        kg_disponiveis = disp["peso_kg"].sum()
c4.metric("Estoque Disponivel", f"{lotes_disponiveis} ({formatar_peso(kg_disponiveis)})")

perda_media = 0
if not df_lav_periodo.empty and "perda_total_kg" in df_lav_periodo.columns and total_fardos_kg > 0:
    df_lav_periodo["perda_total_kg"] = pd.to_numeric(df_lav_periodo["perda_total_kg"], errors="coerce")
    perda_media = (df_lav_periodo["perda_total_kg"].sum() / total_fardos_kg) * 100
c5.metric("Perda Media", formatar_percentual(perda_media))

st.markdown("---")

col_g1, col_g2 = st.columns(2)

with col_g1:
    st.subheader("Producao Mensal")
    if not df_lavacao.empty and not df_extrusao.empty:
        df_lavacao["peso_kg"] = pd.to_numeric(df_lavacao["peso_kg"], errors="coerce")
        df_extrusao["peso_kg"] = pd.to_numeric(df_extrusao["peso_kg"], errors="coerce")
        lav_mensal = df_lavacao.set_index("data").resample("ME")["peso_kg"].sum().tail(6)
        ext_mensal = df_extrusao.set_index("data").resample("ME")["peso_kg"].sum().tail(6)
        fig = go.Figure()
        fig.add_trace(go.Bar(x=lav_mensal.index, y=lav_mensal.values,
                             name="Lavacao (entrada)", marker_color="#4CAF50"))
        fig.add_trace(go.Bar(x=ext_mensal.index, y=ext_mensal.values,
                             name="Extrusao (saida)", marker_color="#2196F3"))
        fig.update_layout(barmode="group", height=350, margin=dict(t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados suficientes para o grafico.")

with col_g2:
    st.subheader("Composicao de Perdas")
    if not df_lav_periodo.empty:
        for col_name in ["perda_lixo_kg", "perda_papelao_kg", "perda_plastico_colorido_kg"]:
            if col_name in df_lav_periodo.columns:
                df_lav_periodo[col_name] = pd.to_numeric(df_lav_periodo[col_name], errors="coerce")
        perdas = {
            "Lixo": df_lav_periodo.get("perda_lixo_kg", pd.Series([0])).sum(),
            "Papelao": df_lav_periodo.get("perda_papelao_kg", pd.Series([0])).sum(),
            "Plastico Colorido": df_lav_periodo.get("perda_plastico_colorido_kg", pd.Series([0])).sum(),
        }
        if sum(perdas.values()) > 0:
            fig = px.pie(values=list(perdas.values()), names=list(perdas.keys()),
                         color_discrete_sequence=["#f44336", "#FF9800", "#9C27B0"],
                         hole=0.3)
            fig.update_layout(height=350, margin=dict(t=20, b=20))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Sem dados de perdas no periodo.")
    else:
        st.info("Sem dados de lavacao no periodo.")

col_g3, col_g4 = st.columns(2)

with col_g3:
    st.subheader("Extrusora A vs B")
    if not df_ext_periodo.empty and "extrusora" in df_ext_periodo.columns:
        por_ext = df_ext_periodo.groupby("extrusora")["peso_kg"].agg(["count", "sum"]).reset_index()
        por_ext.columns = ["Extrusora", "Lotes", "Peso (kg)"]
        fig = px.bar(por_ext, x="Extrusora", y="Peso (kg)", text="Lotes",
                     color="Extrusora", color_discrete_map={"A": "#4CAF50", "B": "#2196F3"})
        fig.update_layout(height=350, margin=dict(t=20, b=20), showlegend=False)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados de extrusao no periodo.")

with col_g4:
    st.subheader("Estoque por Grade")
    if not df_extrusao.empty and not df_qualidade.empty:
        disp = df_extrusao[df_extrusao["status"] == "disponivel"]
        if not disp.empty and "codigo_lote" in disp.columns and "codigo_lote" in df_qualidade.columns:
            merged = disp.merge(df_qualidade[["codigo_lote", "grade"]], on="codigo_lote", how="left")
            merged["peso_kg"] = pd.to_numeric(merged["peso_kg"], errors="coerce")
            por_grade = merged.groupby("grade")["peso_kg"].sum().reset_index()
            por_grade.columns = ["Grade", "Peso (kg)"]
            por_grade = por_grade[por_grade["Grade"].notna() & (por_grade["Grade"] != "")]
            if not por_grade.empty:
                fig = px.bar(por_grade, x="Grade", y="Peso (kg)", color="Grade")
                fig.update_layout(height=350, margin=dict(t=20, b=20), showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Nenhum lote com grade definido em estoque.")
        else:
            st.info("Sem dados para cruzar.")
    else:
        st.info("Sem dados de estoque.")

if not df_par_periodo.empty and "duracao_min" in df_par_periodo.columns:
    st.markdown("---")
    st.subheader("Paradas no Periodo")
    df_par_periodo["duracao_min"] = pd.to_numeric(df_par_periodo["duracao_min"], errors="coerce")
    por_tipo = df_par_periodo.groupby("tipo_parada")["duracao_min"].sum().reset_index()
    por_tipo.columns = ["Tipo", "Minutos"]
    por_tipo["Horas"] = (por_tipo["Minutos"] / 60).round(1)
    fig = px.bar(por_tipo, x="Tipo", y="Horas", text="Horas",
                 color="Tipo", color_discrete_sequence=["#f44336", "#FF9800", "#FFC107"])
    fig.update_layout(height=300, margin=dict(t=20, b=20), showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
