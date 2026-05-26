import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.database import read_sheet
from utils.formatters import (
    formatar_data,
    formatar_peso,
    GRADES,
    CORES,
    EXTRUSORAS,
)

# ---------------------------------------------------------------------------
# Titulo
# ---------------------------------------------------------------------------
st.header("Estoque de Produto Acabado")

# ---------------------------------------------------------------------------
# Carregar dados
# ---------------------------------------------------------------------------
try:
    df_ext = read_sheet("producao_extrusao")
except Exception as exc:
    st.error(f"Erro ao carregar producao: {exc}")
    df_ext = pd.DataFrame()

try:
    df_qual = read_sheet("qualidade")
except Exception as exc:
    st.error(f"Erro ao carregar qualidade: {exc}")
    df_qual = pd.DataFrame()

if df_ext.empty:
    st.info("Nenhum dado de producao encontrado.")
    st.stop()

# Filtrar somente disponiveis
df_disp = df_ext[df_ext["status"] == "disponivel"].copy()

if df_disp.empty:
    st.info("Nenhum lote disponivel em estoque.")
    st.stop()

# Converter peso
df_disp["peso_kg"] = pd.to_numeric(df_disp["peso_kg"], errors="coerce").fillna(0)

# Join com qualidade para trazer grade, cor e local
if not df_qual.empty:
    df_qual_unico = df_qual.drop_duplicates(subset="codigo_lote", keep="last")
    df_estoque = df_disp.merge(
        df_qual_unico[["codigo_lote", "grade", "cor", "local_estoque"]],
        on="codigo_lote",
        how="left",
    )
else:
    df_estoque = df_disp.copy()
    df_estoque["grade"] = ""
    df_estoque["cor"] = ""
    df_estoque["local_estoque"] = ""

# Preencher valores faltantes
df_estoque["grade"] = df_estoque["grade"].fillna("Sem analise")
df_estoque["cor"] = df_estoque["cor"].fillna("")
df_estoque["local_estoque"] = df_estoque["local_estoque"].fillna("")

# Calcular dias em estoque
df_estoque["data_dt"] = pd.to_datetime(df_estoque["data"], errors="coerce").dt.date
df_estoque["dias_em_estoque"] = df_estoque["data_dt"].apply(
    lambda d: (date.today() - d).days if pd.notna(d) else 0
)

# ---------------------------------------------------------------------------
# Metricas resumo
# ---------------------------------------------------------------------------
st.subheader("Resumo")

total_lotes = len(df_estoque)
total_kg = df_estoque["peso_kg"].sum()

col_m1, col_m2, col_m3 = st.columns(3)
with col_m1:
    st.metric("Total de Lotes", total_lotes)
with col_m2:
    st.metric("Peso Total", formatar_peso(total_kg))
with col_m3:
    media_dias = (
        df_estoque["dias_em_estoque"].mean() if total_lotes > 0 else 0
    )
    st.metric("Media Dias em Estoque", f"{media_dias:.0f} dias")

# Resumo por grade
st.caption("Estoque por Grade:")
resumo_grade = (
    df_estoque.groupby("grade")
    .agg(lotes=("codigo_lote", "count"), peso_total=("peso_kg", "sum"))
    .reset_index()
)
resumo_grade["peso_total"] = resumo_grade["peso_total"].apply(formatar_peso)
st.dataframe(resumo_grade, use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------
st.subheader("Filtros")

col_f1, col_f2 = st.columns(2)
with col_f1:
    filtro_grade = st.multiselect(
        "Grade",
        options=sorted(df_estoque["grade"].unique()),
        default=[],
        key="est_filtro_grade",
    )
    filtro_cor = st.multiselect(
        "Cor",
        options=sorted(df_estoque["cor"].dropna().unique()),
        default=[],
        key="est_filtro_cor",
    )
with col_f2:
    filtro_extrusora = st.multiselect(
        "Extrusora",
        options=sorted(df_estoque["extrusora"].unique()),
        default=[],
        key="est_filtro_extrusora",
    )
    col_d1, col_d2 = st.columns(2)
    with col_d1:
        filtro_data_inicio = st.date_input(
            "Data Inicio",
            value=date.today() - timedelta(days=90),
            key="est_data_inicio",
        )
    with col_d2:
        filtro_data_fim = st.date_input(
            "Data Fim", value=date.today(), key="est_data_fim"
        )

# Aplicar filtros
df_view = df_estoque.copy()

if filtro_grade:
    df_view = df_view[df_view["grade"].isin(filtro_grade)]
if filtro_cor:
    df_view = df_view[df_view["cor"].isin(filtro_cor)]
if filtro_extrusora:
    df_view = df_view[df_view["extrusora"].isin(filtro_extrusora)]

df_view = df_view[
    (df_view["data_dt"] >= filtro_data_inicio)
    & (df_view["data_dt"] <= filtro_data_fim)
]

# Ordenar por data decrescente
df_view = df_view.sort_values("data_dt", ascending=False)

st.divider()

# ---------------------------------------------------------------------------
# Tabela principal
# ---------------------------------------------------------------------------
st.subheader("Lotes em Estoque")

if df_view.empty:
    st.info("Nenhum lote encontrado com os filtros selecionados.")
else:
    df_tabela = df_view[
        [
            "codigo_lote",
            "data",
            "tipo_descricao",
            "extrusora",
            "peso_kg",
            "grade",
            "cor",
            "local_estoque",
            "dias_em_estoque",
        ]
    ].copy()

    df_tabela["data"] = df_tabela["data"].apply(formatar_data)

    st.dataframe(df_tabela, use_container_width=True, hide_index=True)

    # Totais
    total_filtrado_lotes = len(df_tabela)
    total_filtrado_kg = df_view["peso_kg"].sum()
    st.markdown(
        f"**Totais filtrados:** {total_filtrado_lotes} lotes | "
        f"{formatar_peso(total_filtrado_kg)}"
    )
