import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.database import read_sheet
from utils.formatters import formatar_data, formatar_peso

# ---------------------------------------------------------------------------
# Titulo e botao de atualizacao
# ---------------------------------------------------------------------------
col_titulo, col_botao = st.columns([4, 1])
with col_titulo:
    st.header("Estoque de Aparas")
with col_botao:
    st.write("")
    if st.button("Atualizar dados", key="estoque_aparas_atualizar"):
        st.cache_data.clear()
        st.rerun()

# ---------------------------------------------------------------------------
# Carregar dados
# ---------------------------------------------------------------------------
try:
    df_aparas = read_sheet("aparas_estoque")
except Exception as exc:
    st.error(f"Erro ao carregar estoque de aparas: {exc}")
    df_aparas = pd.DataFrame()

if df_aparas.empty:
    st.info("Nenhuma NF de apara registrada ainda.")
    st.stop()

# Normalizar colunas
colunas_esperadas = [
    "id", "numero_nf", "fornecedor", "tipo_fardo", "quantidade",
    "peso_kg", "data_recebimento", "qualidade", "status", "opl_em_uso",
    "data_classificacao", "classificado_por", "registrado_por",
    "observacao", "created_at",
]
for col in colunas_esperadas:
    if col not in df_aparas.columns:
        df_aparas[col] = ""

# Converter tipos numericos
df_aparas["peso_kg"] = pd.to_numeric(df_aparas["peso_kg"], errors="coerce").fillna(0)
df_aparas["quantidade"] = pd.to_numeric(df_aparas["quantidade"], errors="coerce").fillna(0).astype(int)

# Normalizar status (vazio = aguardando_classificacao)
df_aparas["status"] = df_aparas["status"].fillna("").astype(str).str.strip()
df_aparas.loc[df_aparas["status"] == "", "status"] = "aguardando_classificacao"

# ---------------------------------------------------------------------------
# Metricas principais
# ---------------------------------------------------------------------------
df_aguardando = df_aparas[df_aparas["status"] == "aguardando_classificacao"].copy()
df_disponivel = df_aparas[df_aparas["status"] == "disponivel"].copy()
df_em_uso = df_aparas[df_aparas["status"] == "em_uso"].copy()

col_m1, col_m2, col_m3, col_m4 = st.columns(4)

with col_m1:
    st.metric(
        "Aguardando classificacao",
        f"{len(df_aguardando)} NFs",
        delta=formatar_peso(df_aguardando["peso_kg"].sum()),
        delta_color="off",
    )
with col_m2:
    st.metric(
        "Disponivel",
        f"{len(df_disponivel)} NFs",
        delta=formatar_peso(df_disponivel["peso_kg"].sum()),
        delta_color="off",
    )
with col_m3:
    st.metric(
        "Em uso (OPL)",
        f"{len(df_em_uso)} NFs",
        delta=formatar_peso(df_em_uso["peso_kg"].sum()),
        delta_color="off",
    )
with col_m4:
    st.metric(
        "Total no estoque",
        f"{len(df_aparas)} NFs",
        delta=formatar_peso(df_aparas["peso_kg"].sum()),
        delta_color="off",
    )

st.divider()

# ---------------------------------------------------------------------------
# Secao 1: Aguardando Classificacao
# ---------------------------------------------------------------------------
st.subheader("Aguardando Classificacao")

if df_aguardando.empty:
    st.caption("Nenhuma NF aguardando classificacao.")
else:
    df_ag_view = df_aguardando[
        [
            "numero_nf",
            "fornecedor",
            "tipo_fardo",
            "quantidade",
            "peso_kg",
            "data_recebimento",
            "registrado_por",
            "observacao",
        ]
    ].copy()

    df_ag_view["data_recebimento"] = df_ag_view["data_recebimento"].apply(formatar_data)
    df_ag_view["peso_kg"] = df_ag_view["peso_kg"].apply(formatar_peso)

    df_ag_view = df_ag_view.rename(
        columns={
            "numero_nf": "NF",
            "fornecedor": "Fornecedor",
            "tipo_fardo": "Tipo de Fardo",
            "quantidade": "Quantidade",
            "peso_kg": "Peso",
            "data_recebimento": "Data Recebimento",
            "registrado_por": "Registrado por",
            "observacao": "Observacao",
        }
    )

    st.dataframe(df_ag_view, use_container_width=True, hide_index=True)
    st.markdown(
        f"**Total aguardando:** {len(df_aguardando)} NFs | "
        f"{formatar_peso(df_aguardando['peso_kg'].sum())}"
    )

st.divider()

# ---------------------------------------------------------------------------
# Secao 2: Disponivel para Producao
# ---------------------------------------------------------------------------
st.subheader("Disponivel para Producao")

if df_disponivel.empty:
    st.caption("Nenhuma NF disponivel para producao.")
else:
    # Filtros
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        opcoes_qualidade = sorted(
            [q for q in df_disponivel["qualidade"].dropna().unique() if str(q).strip() != ""]
        )
        if not opcoes_qualidade:
            opcoes_qualidade = ["A", "B", "C"]
        filtro_qualidade = st.multiselect(
            "Qualidade",
            options=["A", "B", "C"],
            default=[],
            key="estoque_aparas_filtro_qualidade",
        )
    with col_f2:
        filtro_fornecedor = st.text_input(
            "Fornecedor (contem)",
            value="",
            key="estoque_aparas_filtro_fornecedor",
        )

    df_disp_view = df_disponivel.copy()

    if filtro_qualidade:
        df_disp_view = df_disp_view[df_disp_view["qualidade"].isin(filtro_qualidade)]
    if filtro_fornecedor.strip():
        df_disp_view = df_disp_view[
            df_disp_view["fornecedor"]
            .astype(str)
            .str.contains(filtro_fornecedor.strip(), case=False, na=False)
        ]

    if df_disp_view.empty:
        st.info("Nenhuma NF encontrada com os filtros selecionados.")
    else:
        df_disp_tab = df_disp_view[
            [
                "numero_nf",
                "fornecedor",
                "qualidade",
                "tipo_fardo",
                "quantidade",
                "peso_kg",
                "data_recebimento",
                "data_classificacao",
                "classificado_por",
            ]
        ].copy()

        df_disp_tab["data_recebimento"] = df_disp_tab["data_recebimento"].apply(formatar_data)
        df_disp_tab["data_classificacao"] = df_disp_tab["data_classificacao"].apply(formatar_data)
        df_disp_tab["peso_kg"] = df_disp_tab["peso_kg"].apply(formatar_peso)

        df_disp_tab = df_disp_tab.rename(
            columns={
                "numero_nf": "NF",
                "fornecedor": "Fornecedor",
                "qualidade": "Qualidade",
                "tipo_fardo": "Tipo de Fardo",
                "quantidade": "Quantidade",
                "peso_kg": "Peso",
                "data_recebimento": "Data Recebimento",
                "data_classificacao": "Data Classificacao",
                "classificado_por": "Classificado por",
            }
        )

        st.dataframe(df_disp_tab, use_container_width=True, hide_index=True)

        st.markdown(
            f"**Total filtrado:** {len(df_disp_view)} NFs | "
            f"{formatar_peso(df_disp_view['peso_kg'].sum())}"
        )

    # Total disponivel por qualidade (sempre baseado em df_disponivel completo)
    st.caption("Total disponivel por qualidade:")
    col_qa, col_qb, col_qc = st.columns(3)

    df_qa = df_disponivel[df_disponivel["qualidade"] == "A"]
    df_qb = df_disponivel[df_disponivel["qualidade"] == "B"]
    df_qc = df_disponivel[df_disponivel["qualidade"] == "C"]

    with col_qa:
        st.metric(
            "Qualidade A",
            f"{len(df_qa)} NFs",
            delta=formatar_peso(df_qa["peso_kg"].sum()),
            delta_color="off",
        )
    with col_qb:
        st.metric(
            "Qualidade B",
            f"{len(df_qb)} NFs",
            delta=formatar_peso(df_qb["peso_kg"].sum()),
            delta_color="off",
        )
    with col_qc:
        st.metric(
            "Qualidade C",
            f"{len(df_qc)} NFs",
            delta=formatar_peso(df_qc["peso_kg"].sum()),
            delta_color="off",
        )

st.divider()

# ---------------------------------------------------------------------------
# Secao 3: Em Uso (OPL)
# ---------------------------------------------------------------------------
st.subheader("Em Uso (OPL)")

if df_em_uso.empty:
    st.caption("Nenhuma NF em uso em OPL.")
else:
    df_uso_view = df_em_uso[
        [
            "numero_nf",
            "fornecedor",
            "qualidade",
            "tipo_fardo",
            "quantidade",
            "peso_kg",
            "opl_em_uso",
        ]
    ].copy()

    df_uso_tab = df_uso_view.copy()
    df_uso_tab["peso_kg"] = df_uso_tab["peso_kg"].apply(formatar_peso)

    df_uso_tab = df_uso_tab.rename(
        columns={
            "numero_nf": "NF",
            "fornecedor": "Fornecedor",
            "qualidade": "Qualidade",
            "tipo_fardo": "Tipo de Fardo",
            "quantidade": "Quantidade",
            "peso_kg": "Peso",
            "opl_em_uso": "OPL em uso",
        }
    )

    st.dataframe(df_uso_tab, use_container_width=True, hide_index=True)

    st.markdown(
        f"**Total em uso:** {len(df_em_uso)} NFs | "
        f"{formatar_peso(df_em_uso['peso_kg'].sum())}"
    )

    # Agrupamento por OPL
    st.caption("Total por OPL:")
    df_opl_grupo = (
        df_em_uso.groupby("opl_em_uso", dropna=False)
        .agg(
            nfs=("numero_nf", "count"),
            quantidade_fardos=("quantidade", "sum"),
            peso_total_kg=("peso_kg", "sum"),
        )
        .reset_index()
        .rename(
            columns={
                "opl_em_uso": "OPL",
                "nfs": "NFs",
                "quantidade_fardos": "Fardos",
                "peso_total_kg": "Peso Total",
            }
        )
    )

    df_opl_grupo["OPL"] = df_opl_grupo["OPL"].fillna("(sem OPL)").replace("", "(sem OPL)")
    df_opl_grupo["Peso Total"] = df_opl_grupo["Peso Total"].apply(formatar_peso)
    df_opl_grupo = df_opl_grupo.sort_values("OPL")

    st.dataframe(df_opl_grupo, use_container_width=True, hide_index=True)
