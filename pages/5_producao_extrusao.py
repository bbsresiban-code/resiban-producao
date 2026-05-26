import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, time

from utils.database import read_sheet, append_row
from utils.serial_code import gerar_codigo_serial, preview_codigo
from utils.formatters import (
    TURNOS,
    EXTRUSORAS,
    TIPOS_PRODUTO,
    formatar_peso,
    formatar_data,
)

st.title("Producao Extrusao")

tab_lote, tab_manut, tab_hist = st.tabs(["Novo Lote", "Manutencao", "Historico"])

# ---------------------------------------------------------------------------
# Tab: Novo Lote
# ---------------------------------------------------------------------------
with tab_lote:
    st.subheader("Registrar Novo Lote de Extrusao")

    # --- Fetch open OPs ---
    try:
        df_ops = read_sheet("op_extrusao")
    except Exception as exc:
        st.error(f"Erro ao carregar OPs: {exc}")
        df_ops = pd.DataFrame()

    ops_abertas = []
    if not df_ops.empty and "status" in df_ops.columns:
        ops_abertas = df_ops[df_ops["status"] == "aberta"]["numero_op"].tolist()

    if not ops_abertas:
        st.warning("Nenhuma OP de extrusao aberta. Crie uma OP antes de registrar lotes.")
    else:
        # --- Selectors outside the form for live preview ---
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            data_lote = st.date_input("Data", value=date.today(), key="lote_data")
        with col_s2:
            turno = st.selectbox("Turno", options=TURNOS, key="lote_turno")
        with col_s3:
            numero_op = st.selectbox("Numero da OP", options=ops_abertas, key="lote_op")

        # Tipo and Extrusora outside form for live preview
        opcoes_tipo = {k: f"{k} - {v}" for k, v in TIPOS_PRODUTO.items()}
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            tipo = st.selectbox(
                "Tipo",
                options=list(opcoes_tipo.keys()),
                format_func=lambda x: opcoes_tipo[x],
                key="lote_tipo",
            )
        with col_t2:
            extrusora = st.radio(
                "Extrusora",
                options=EXTRUSORAS,
                horizontal=True,
                key="lote_extrusora",
            )

        # --- Serial code preview ---
        codigo_preview = preview_codigo(tipo, extrusora, data_lote)
        st.info(f"Codigo do lote (preview): **{codigo_preview}**")

        # --- Form for remaining fields ---
        with st.form("form_novo_lote", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                peso_kg = st.number_input(
                    "Peso (kg)", min_value=0.0, step=0.5, format="%.1f"
                )
                hora = st.time_input("Hora", value=time(8, 0))
            with col_f2:
                observacao_lote = st.text_input("Observacao")
                registrado_por = st.text_input("Registrado por")

            submitted = st.form_submit_button(
                "Registrar Lote", use_container_width=True, type="primary"
            )

            if submitted:
                erros = []
                if peso_kg <= 0:
                    erros.append("Peso deve ser maior que zero.")
                if not registrado_por.strip():
                    erros.append("Campo 'Registrado por' e obrigatorio.")

                if erros:
                    for e in erros:
                        st.error(e)
                else:
                    try:
                        codigo_lote, sequencial = gerar_codigo_serial(
                            tipo, extrusora, data_lote
                        )

                        dados = {
                            "data": data_lote.isoformat(),
                            "turno": turno,
                            "hora": hora.strftime("%H:%M"),
                            "numero_op": numero_op,
                            "codigo_lote": codigo_lote,
                            "tipo": tipo,
                            "tipo_descricao": TIPOS_PRODUTO[tipo],
                            "extrusora": extrusora,
                            "peso_kg": peso_kg,
                            "mes": data_lote.month,
                            "ano": data_lote.year % 100,
                            "sequencial": sequencial,
                            "status": "em_analise",
                            "observacao_lote": observacao_lote.strip(),
                            "registrado_por": registrado_por.strip(),
                        }

                        append_row("producao_extrusao", dados)
                        st.success(
                            f"Lote registrado com sucesso!  \n"
                            f"### Codigo: `{codigo_lote}`"
                        )
                        st.balloons()
                    except Exception as exc:
                        st.error(f"Erro ao registrar lote: {exc}")

# ---------------------------------------------------------------------------
# Tab: Manutencao
# ---------------------------------------------------------------------------
with tab_manut:
    st.subheader("Registro de Manutencao - Extrusao")

    with st.form("form_manutencao_extrusao", clear_on_submit=True):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            data_manut = st.date_input("Data", value=date.today(), key="manut_data")
            turno_manut = st.selectbox("Turno", options=TURNOS, key="manut_turno")
        with col_m2:
            troca_telas = st.text_input("Troca de Telas")
            limpeza_gaveta = st.text_input("Limpeza de Gaveta")

        troca_facas = st.text_input("Troca de Facas")
        observacao_manut = st.text_area("Observacao")

        submitted_manut = st.form_submit_button(
            "Registrar Manutencao", use_container_width=True
        )

        if submitted_manut:
            try:
                dados_manut = {
                    "data": data_manut.isoformat(),
                    "turno": turno_manut,
                    "troca_telas": troca_telas.strip(),
                    "limpeza_gaveta": limpeza_gaveta.strip(),
                    "troca_facas": troca_facas.strip(),
                    "observacao": observacao_manut.strip(),
                }
                append_row("manutencao_extrusao", dados_manut)
                st.success("Manutencao registrada com sucesso!")
            except Exception as exc:
                st.error(f"Erro ao registrar manutencao: {exc}")

# ---------------------------------------------------------------------------
# Tab: Historico
# ---------------------------------------------------------------------------
with tab_hist:
    st.subheader("Historico de Producao - Extrusao")

    # Filters
    col_h1, col_h2, col_h3 = st.columns(3)
    with col_h1:
        hist_inicio = st.date_input(
            "Data Inicio",
            value=date.today().replace(day=1),
            key="hist_ini",
        )
        hist_fim = st.date_input("Data Fim", value=date.today(), key="hist_fim")
    with col_h2:
        hist_turno = st.multiselect("Turno", options=TURNOS, default=TURNOS, key="hist_turno")
    with col_h3:
        hist_extrusora = st.multiselect(
            "Extrusora", options=EXTRUSORAS, default=EXTRUSORAS, key="hist_ext"
        )

    try:
        df_hist = read_sheet("producao_extrusao")
    except Exception as exc:
        st.error(f"Erro ao carregar historico: {exc}")
        df_hist = pd.DataFrame()

    if not df_hist.empty:
        df_hist["data_dt"] = pd.to_datetime(df_hist["data"], errors="coerce")
        mask = (
            (df_hist["data_dt"] >= pd.Timestamp(hist_inicio))
            & (df_hist["data_dt"] <= pd.Timestamp(hist_fim))
        )
        if hist_turno:
            mask = mask & (df_hist["turno"].isin(hist_turno))
        if hist_extrusora:
            mask = mask & (df_hist["extrusora"].isin(hist_extrusora))

        df_filtrado = df_hist[mask].copy()

        if df_filtrado.empty:
            st.info("Nenhum lote encontrado para os filtros selecionados.")
        else:
            # Color-code status
            def cor_status(val):
                cores = {
                    "em_analise": "background-color: #fff3cd; color: #856404",
                    "disponivel": "background-color: #d4edda; color: #155724",
                    "carregado": "background-color: #e2e3e5; color: #383d41",
                }
                return cores.get(val, "")

            colunas_exibir = [
                c for c in [
                    "codigo_lote", "data", "turno", "numero_op", "extrusora",
                    "tipo_descricao", "peso_kg", "status", "registrado_por",
                ] if c in df_filtrado.columns
            ]

            styled_df = df_filtrado[colunas_exibir].sort_values(
                "data", ascending=False
            )

            if "status" in styled_df.columns:
                st.dataframe(
                    styled_df.style.map(cor_status, subset=["status"]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                )

            # Summary metrics
            st.markdown("---")
            st.subheader("Resumo do Periodo")

            df_filtrado["peso_kg_num"] = pd.to_numeric(
                df_filtrado["peso_kg"], errors="coerce"
            )

            total_lotes = len(df_filtrado)
            total_kg = df_filtrado["peso_kg_num"].sum()

            col_met1, col_met2 = st.columns(2)
            with col_met1:
                st.metric("Total de Lotes", total_lotes)
            with col_met2:
                st.metric("Total Produzido", formatar_peso(total_kg))

            # By extruder
            if "extrusora" in df_filtrado.columns:
                st.markdown("**Producao por Extrusora:**")
                resumo_ext = (
                    df_filtrado.groupby("extrusora")
                    .agg(
                        lotes=("extrusora", "count"),
                        peso_total=("peso_kg_num", "sum"),
                    )
                    .reset_index()
                )
                resumo_ext["peso_total"] = resumo_ext["peso_total"].apply(formatar_peso)
                resumo_ext.columns = ["Extrusora", "Lotes", "Peso Total"]
                st.dataframe(resumo_ext, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado de producao encontrado.")
