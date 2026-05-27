import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.database import read_sheet, read_sheet_no_cache, append_row, update_rows
from utils.formatters import (
    formatar_data,
    formatar_peso,
    GRADES,
    CORES,
    LOCAIS_ESTOQUE,
)

# ---------------------------------------------------------------------------
# Titulo
# ---------------------------------------------------------------------------
st.header("Laboratorio de Qualidade")

tab_analisar, tab_historico = st.tabs(["Analisar Lote", "Historico"])

# ===========================================================================
# TAB: Analisar Lote
# ===========================================================================
with tab_analisar:
    st.subheader("Analise de Lote")

    # Carregar lotes com status em_analise
    try:
        df_ext = read_sheet_no_cache("producao_extrusao")
    except Exception as exc:
        st.error(f"Erro ao carregar lotes: {exc}")
        df_ext = pd.DataFrame()

    if df_ext.empty:
        st.info("Nenhum lote disponivel para analise.")
    else:
        df_em_analise = df_ext[df_ext["status"] == "em_analise"].copy()

        if df_em_analise.empty:
            st.info("Nenhum lote com status 'em_analise' encontrado.")
        else:
            # Garantir que peso_kg seja numerico para exibicao
            df_em_analise["peso_kg"] = pd.to_numeric(
                df_em_analise["peso_kg"], errors="coerce"
            ).fillna(0)

            # Tabela de lotes em analise
            st.caption("Lotes aguardando analise:")
            st.dataframe(
                df_em_analise[
                    ["codigo_lote", "data", "tipo_descricao", "extrusora", "peso_kg"]
                ],
                use_container_width=True,
                hide_index=True,
            )

            # Selectbox para escolher o lote
            opcoes_lote = [
                f"{row['codigo_lote']} | {formatar_peso(row['peso_kg'])}"
                for _, row in df_em_analise.iterrows()
            ]
            lote_selecionado_label = st.selectbox(
                "Selecione o lote para analise", options=opcoes_lote
            )

            if lote_selecionado_label:
                codigo_lote_sel = lote_selecionado_label.split(" | ")[0]

                st.divider()

                with st.form("form_analise_qualidade", clear_on_submit=True):
                    st.markdown(f"**Lote:** `{codigo_lote_sel}`")

                    col1, col2 = st.columns(2)
                    with col1:
                        mfi_txt = st.text_input(
                            "MFI (g/10min)", help="Use virgula ou ponto. Ex: 0,8 ou 1.3"
                        )
                        teor_cinzas_txt = st.text_input(
                            "Teor de Cinzas (%) - opcional", help="Deixe vazio se nao aplicavel"
                        )
                        densidade_txt = st.text_input(
                            "Densidade (g/cm3) - opcional", help="Deixe vazio se nao aplicavel"
                        )
                        umidade_txt = st.text_input(
                            "Umidade (%)", help="Use virgula ou ponto. Ex: 0,5"
                        )
                        teste_filme = st.selectbox(
                            "Teste de Filme", options=["OK", "Anomalia"]
                        )

                    with col2:
                        grade = st.selectbox("Grade", options=GRADES)
                        cor = st.selectbox("Cor", options=CORES)
                        analista = st.text_input("Analista")
                        data_analise = st.date_input("Data da Analise", value=date.today())

                    observacao = st.text_area("Observacao")

                    submitted = st.form_submit_button(
                        "Registrar Analise", type="primary", use_container_width=True
                    )

                if submitted:
                    def _parse_numero(txt):
                        if not txt or not txt.strip():
                            return ""
                        return txt.strip().replace(",", ".")

                    mfi = _parse_numero(mfi_txt)
                    teor_cinzas = _parse_numero(teor_cinzas_txt)
                    densidade = _parse_numero(densidade_txt)
                    umidade = _parse_numero(umidade_txt)

                    erros = []
                    if not analista.strip():
                        erros.append("Analista e obrigatorio.")
                    if not mfi:
                        erros.append("MFI e obrigatorio.")

                    if erros:
                        for e in erros:
                            st.error(e)
                    else:
                        try:
                            analise_data = {
                                "codigo_lote": codigo_lote_sel,
                                "mfi": mfi,
                                "teor_cinzas": teor_cinzas,
                                "densidade": densidade,
                                "umidade": umidade,
                                "teste_filme": teste_filme,
                                "grade": grade,
                                "cor": cor,
                                "local_estoque": "",
                                "analista": analista.strip(),
                                "data_analise": data_analise.isoformat(),
                                "observacao": observacao.strip(),
                            }
                            append_row("qualidade", analise_data)

                            # Atualizar status do lote para disponivel
                            update_rows(
                                "producao_extrusao",
                                match_col="codigo_lote",
                                match_values=[codigo_lote_sel],
                                update_col="status",
                                new_value="disponivel",
                            )

                            resultado_completo = f"{grade} - {cor}"
                            st.toast("Analise registrada com sucesso!")
                            st.success(
                                f"Analise do lote **{codigo_lote_sel}** registrada. "
                                f"Resultado: **{resultado_completo}**"
                            )
                        except Exception as exc:
                            st.error(f"Erro ao registrar analise: {exc}")


# ===========================================================================
# TAB: Historico
# ===========================================================================
with tab_historico:
    st.subheader("Historico de Analises")

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        hist_data_inicio = st.date_input(
            "Data Inicio",
            value=date.today() - timedelta(days=30),
            key="qual_hist_inicio",
        )
    with col_f2:
        hist_data_fim = st.date_input(
            "Data Fim", value=date.today(), key="qual_hist_fim"
        )
    with col_f3:
        filtro_grade = st.multiselect(
            "Filtrar por Grade", options=GRADES, default=[], key="qual_hist_grade"
        )

    try:
        df_qual = read_sheet("qualidade")
    except Exception as exc:
        st.error(f"Erro ao carregar historico: {exc}")
        df_qual = pd.DataFrame()

    if df_qual.empty:
        st.info("Nenhuma analise encontrada.")
    else:
        df_qual["data_analise_dt"] = pd.to_datetime(
            df_qual["data_analise"], errors="coerce"
        ).dt.date

        mask = (df_qual["data_analise_dt"] >= hist_data_inicio) & (
            df_qual["data_analise_dt"] <= hist_data_fim
        )
        df_filtrado = df_qual[mask].copy()

        if filtro_grade:
            df_filtrado = df_filtrado[df_filtrado["grade"].isin(filtro_grade)]

        if df_filtrado.empty:
            st.info("Nenhuma analise encontrada no periodo selecionado.")
        else:
            df_filtrado = df_filtrado.sort_values("data_analise_dt", ascending=False)

            df_exibir = df_filtrado[
                [
                    "codigo_lote",
                    "data_analise",
                    "mfi",
                    "teor_cinzas",
                    "densidade",
                    "umidade",
                    "teste_filme",
                    "grade",
                    "cor",
                    "local_estoque",
                    "analista",
                    "observacao",
                ]
            ].copy()
            df_exibir["data_analise"] = df_exibir["data_analise"].apply(formatar_data)

            st.dataframe(df_exibir, use_container_width=True, hide_index=True)
            st.caption(f"Total de registros: {len(df_exibir)}")
