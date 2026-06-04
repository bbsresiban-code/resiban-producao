import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.database import read_sheet, read_sheet_no_cache, append_row
from utils.formatters import formatar_data, formatar_peso

# ---------------------------------------------------------------------------
# Usuario logado
# ---------------------------------------------------------------------------
usuario_logado = st.session_state.get("usuario", "")

# ---------------------------------------------------------------------------
# Titulo
# ---------------------------------------------------------------------------
st.header("Recebimento de Materia Prima")

tab_novo, tab_historico = st.tabs(["Novo Recebimento", "Historico"])

# ===========================================================================
# TAB: Novo Recebimento
# ===========================================================================
with tab_novo:
    st.subheader("Registrar nova NF de aparas")

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        data_recebimento = st.date_input(
            "Data do Recebimento",
            value=date.today(),
            key="rec_data",
        )
    with col_d2:
        registrado_por = st.text_input(
            "Registrado Por *",
            value=usuario_logado,
            key="rec_registrado_por",
        )

    st.divider()

    col_n1, col_n2 = st.columns(2)
    with col_n1:
        numero_nf = st.text_input("Numero da NF *", key="rec_numero_nf")
    with col_n2:
        fornecedor = st.text_input("Fornecedor *", key="rec_fornecedor")

    col_t1, col_t2, col_t3 = st.columns(3)
    with col_t1:
        tipo_fardo = st.selectbox(
            "Tipo de Fardo *",
            options=["Fardinho", "Fardao"],
            key="rec_tipo_fardo",
        )
    with col_t2:
        quantidade = st.number_input(
            "Quantidade *",
            min_value=1,
            step=1,
            value=1,
            key="rec_quantidade",
        )
    with col_t3:
        peso_kg = st.number_input(
            "Peso (kg) *",
            min_value=0.0,
            step=0.5,
            format="%.1f",
            value=0.0,
            key="rec_peso_kg",
        )

    observacao = st.text_input("Observacao", key="rec_observacao")

    st.divider()

    if st.button(
        "Registrar Recebimento",
        type="primary",
        use_container_width=True,
        key="rec_btn_registrar",
    ):
        erros = []
        if not numero_nf.strip():
            erros.append("Informe o numero da NF.")
        if not fornecedor.strip():
            erros.append("Informe o fornecedor.")
        if not tipo_fardo:
            erros.append("Selecione o tipo de fardo.")
        if quantidade < 1:
            erros.append("Quantidade deve ser maior que zero.")
        if peso_kg <= 0:
            erros.append("Peso deve ser maior que zero.")
        if not registrado_por.strip():
            erros.append("Informe o nome do responsavel pelo registro.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            try:
                dados = {
                    "numero_nf": numero_nf.strip(),
                    "fornecedor": fornecedor.strip(),
                    "tipo_fardo": tipo_fardo,
                    "quantidade": int(quantidade),
                    "peso_kg": float(peso_kg),
                    "data_recebimento": data_recebimento.isoformat(),
                    "qualidade": "",
                    "status": "aguardando_classificacao",
                    "opl_em_uso": "",
                    "data_classificacao": "",
                    "classificado_por": "",
                    "registrado_por": registrado_por.strip(),
                    "observacao": observacao.strip(),
                }
                append_row("aparas_estoque", dados)

                st.toast("Recebimento registrado com sucesso!")
                st.success(
                    f"NF **{numero_nf.strip()}** registrada com sucesso!  \n"
                    f"**Fornecedor:** {fornecedor.strip()}  \n"
                    f"**Tipo de Fardo:** {tipo_fardo}  \n"
                    f"**Quantidade:** {int(quantidade)} fardos  \n"
                    f"**Peso:** {formatar_peso(float(peso_kg))}  \n"
                    f"**Status:** aguardando_classificacao"
                )
                st.balloons()
            except Exception as exc:
                st.error(f"Erro ao registrar recebimento: {exc}")

# ===========================================================================
# TAB: Historico
# ===========================================================================
with tab_historico:
    st.subheader("Historico de Recebimentos")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        hist_data_inicio = st.date_input(
            "Data Inicio",
            value=date.today() - timedelta(days=30),
            key="rec_hist_inicio",
        )
    with col_f2:
        hist_data_fim = st.date_input(
            "Data Fim",
            value=date.today(),
            key="rec_hist_fim",
        )

    try:
        df_apa = read_sheet("aparas_estoque")
    except Exception as exc:
        st.error(f"Erro ao carregar historico: {exc}")
        df_apa = pd.DataFrame()

    if df_apa.empty:
        st.info("Nenhum recebimento encontrado.")
    else:
        df_apa["peso_kg"] = pd.to_numeric(
            df_apa["peso_kg"], errors="coerce"
        ).fillna(0)
        df_apa["quantidade"] = pd.to_numeric(
            df_apa["quantidade"], errors="coerce"
        ).fillna(0).astype(int)
        df_apa["data_dt"] = pd.to_datetime(
            df_apa["data_recebimento"], errors="coerce"
        ).dt.date

        # Filtros adicionais
        status_disponiveis = sorted(
            [s for s in df_apa["status"].dropna().unique().tolist() if str(s).strip()]
        )

        col_fs1, col_fs2 = st.columns(2)
        with col_fs1:
            filtro_status = st.multiselect(
                "Filtrar por Status",
                options=status_disponiveis,
                default=status_disponiveis,
                key="rec_filtro_status",
            )
        with col_fs2:
            filtro_fornecedor = st.text_input(
                "Filtrar por Fornecedor (contem)",
                key="rec_filtro_fornecedor",
            )

        # Aplicar filtros
        mask = (df_apa["data_dt"] >= hist_data_inicio) & (
            df_apa["data_dt"] <= hist_data_fim
        )

        if filtro_status:
            mask = mask & df_apa["status"].isin(filtro_status)

        if filtro_fornecedor.strip():
            mask = mask & df_apa["fornecedor"].astype(str).str.contains(
                filtro_fornecedor.strip(), case=False, na=False
            )

        df_filtrado = df_apa[mask].copy()

        if df_filtrado.empty:
            st.info("Nenhum recebimento encontrado com os filtros selecionados.")
        else:
            df_filtrado = df_filtrado.sort_values("data_dt", ascending=False)

            colunas_exibir = [
                c for c in [
                    "numero_nf", "fornecedor", "tipo_fardo", "quantidade",
                    "peso_kg", "data_recebimento", "qualidade", "status",
                    "opl_em_uso",
                ] if c in df_filtrado.columns
            ]

            df_exibir = df_filtrado[colunas_exibir].copy()

            if "data_recebimento" in df_exibir.columns:
                df_exibir["data_recebimento"] = df_exibir["data_recebimento"].apply(
                    formatar_data
                )

            st.dataframe(
                df_exibir,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "numero_nf": st.column_config.TextColumn("NF"),
                    "fornecedor": st.column_config.TextColumn("Fornecedor"),
                    "tipo_fardo": st.column_config.TextColumn("Tipo Fardo"),
                    "quantidade": st.column_config.NumberColumn(
                        "Qtd", format="%d"
                    ),
                    "peso_kg": st.column_config.NumberColumn(
                        "Peso (kg)", format="%.1f"
                    ),
                    "data_recebimento": st.column_config.TextColumn(
                        "Data Recebimento"
                    ),
                    "qualidade": st.column_config.TextColumn("Qualidade"),
                    "status": st.column_config.TextColumn("Status"),
                    "opl_em_uso": st.column_config.TextColumn("OPL em Uso"),
                },
            )

            # Resumo
            st.markdown("---")
            st.subheader("Resumo do Periodo")

            total_nfs = df_filtrado["numero_nf"].nunique()
            peso_total = df_filtrado["peso_kg"].sum()
            qtd_aguardando = int(
                (df_filtrado["status"] == "aguardando_classificacao").sum()
            )

            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Total de NFs", total_nfs)
            with col_r2:
                st.metric("Peso Total", formatar_peso(peso_total))
            with col_r3:
                st.metric(
                    "Aguardando Classificacao", qtd_aguardando
                )
