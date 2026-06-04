import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.database import read_sheet, read_sheet_no_cache, append_row, update_rows, update_row_multi
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

tab_analisar, tab_editar, tab_historico = st.tabs(["Analisar Lote", "Editar Analise", "Historico"])

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
                st.markdown(f"**Lote:** `{codigo_lote_sel}`")

                def _grade_por_mfi(mfi_str):
                    try:
                        v = float(str(mfi_str).replace(",", "."))
                    except (ValueError, TypeError):
                        return ""
                    if v <= 0.29:
                        return "RESI03CR"
                    elif v <= 0.79:
                        return "RESI02CI"
                    elif v <= 1.2:
                        return "RESI01C"
                    elif v <= 1.99:
                        return "RESI04CS"
                    elif v <= 6.0:
                        return "RESI06S"
                    return ""

                mfi_txt = st.text_input(
                    "MFI (g/10min)", help="Use virgula ou ponto. Ex: 0,8 ou 1.3",
                    key="qual_mfi",
                )

                grade_auto = _grade_por_mfi(mfi_txt)
                if grade_auto:
                    st.success(f"Grade sugerido: **{grade_auto}**")
                    idx_grade = GRADES.index(grade_auto) if grade_auto in GRADES else 0
                else:
                    idx_grade = 0

                col1, col2 = st.columns(2)
                with col1:
                    grade = st.selectbox("Grade", options=GRADES, index=idx_grade, key="qual_grade")
                    cor = st.selectbox("Cor", options=CORES, key="qual_cor")
                    umidade_txt = st.text_input(
                        "Umidade (%)", help="Use virgula ou ponto. Ex: 0,5",
                        key="qual_umidade",
                    )
                    teste_filme = st.selectbox(
                        "Teste de Filme", options=["OK", "Anomalia"], key="qual_filme"
                    )
                with col2:
                    teor_cinzas_txt = st.text_input(
                        "Teor de Cinzas (%) - opcional", help="Deixe vazio se nao aplicavel",
                        key="qual_cinzas",
                    )
                    densidade_txt = st.text_input(
                        "Densidade (g/cm3) - opcional", help="Deixe vazio se nao aplicavel",
                        key="qual_dens",
                    )
                    analista = st.text_input("Analista", key="qual_analista")
                    data_analise = st.date_input("Data da Analise", value=date.today(), key="qual_data")

                observacao = st.text_area("Observacao", key="qual_obs")

                submitted = st.button(
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
# TAB: Editar Analise
# ===========================================================================
with tab_editar:
    st.subheader("Editar Analise de Lote")
    st.caption("Altere os resultados de uma analise ja registrada.")

    try:
        df_qual_edit = read_sheet_no_cache("qualidade")
    except Exception as exc:
        st.error(f"Erro ao carregar analises: {exc}")
        df_qual_edit = pd.DataFrame()

    if df_qual_edit.empty:
        st.info("Nenhuma analise registrada ainda.")
    else:
        opcoes_lotes = df_qual_edit["codigo_lote"].astype(str).unique().tolist()
        lote_edit = st.selectbox(
            "Selecione o lote para editar", options=sorted(opcoes_lotes), key="edit_lote_sel"
        )

        if lote_edit:
            analises_lote = df_qual_edit[df_qual_edit["codigo_lote"].astype(str) == lote_edit]
            analise_atual = analises_lote.iloc[-1]
            analise_id = str(analise_atual["id"])

            st.markdown(f"**Lote:** `{lote_edit}` | **Analista atual:** {analise_atual.get('analista', '')} | **Data:** {formatar_data(analise_atual.get('data_analise', ''))}")
            st.divider()

            def _gp_mfi(s):
                try:
                    v = float(str(s).replace(",", "."))
                except (ValueError, TypeError):
                    return ""
                if v <= 0.29:
                    return "RESI03CR"
                elif v <= 0.79:
                    return "RESI02CI"
                elif v <= 1.2:
                    return "RESI01C"
                elif v <= 1.99:
                    return "RESI04CS"
                elif v <= 6.0:
                    return "RESI06S"
                return ""

            mfi_edit = st.text_input(
                "MFI (g/10min)", value=str(analise_atual.get("mfi", "")),
                key="edit_mfi", help="Use virgula ou ponto",
            )
            grade_sug = _gp_mfi(mfi_edit)
            if grade_sug:
                st.success(f"Grade sugerido pelo MFI: **{grade_sug}**")

            col_e1, col_e2 = st.columns(2)
            with col_e1:
                grade_atual = str(analise_atual.get("grade", ""))
                idx_g = GRADES.index(grade_atual) if grade_atual in GRADES else (GRADES.index(grade_sug) if grade_sug in GRADES else 0)
                grade_edit = st.selectbox("Grade", options=GRADES, index=idx_g, key="edit_grade")

                cor_atual = str(analise_atual.get("cor", ""))
                idx_c = CORES.index(cor_atual) if cor_atual in CORES else 0
                cor_edit = st.selectbox("Cor", options=CORES, index=idx_c, key="edit_cor")

                umidade_edit = st.text_input("Umidade (%)", value=str(analise_atual.get("umidade", "")), key="edit_umidade")
                tf_atual = str(analise_atual.get("teste_filme", "OK"))
                tf_edit = st.selectbox("Teste de Filme", ["OK", "Anomalia"], index=0 if tf_atual == "OK" else 1, key="edit_tf")
            with col_e2:
                cinzas_edit = st.text_input("Teor de Cinzas (%) - opcional", value=str(analise_atual.get("teor_cinzas", "")), key="edit_cinzas")
                dens_edit = st.text_input("Densidade (g/cm3) - opcional", value=str(analise_atual.get("densidade", "")), key="edit_dens")
                analista_edit = st.text_input("Analista", value=str(analise_atual.get("analista", "")), key="edit_analista")
                obs_edit = st.text_input("Observacao", value=str(analise_atual.get("observacao", "")), key="edit_obs")

            if st.button("Salvar Alteracoes", type="primary", use_container_width=True, key="btn_edit_salvar"):
                def _pn(t):
                    t = str(t or "").strip()
                    return t.replace(",", ".") if t else ""

                try:
                    novos_valores = {
                        "mfi": _pn(mfi_edit),
                        "teor_cinzas": _pn(cinzas_edit),
                        "densidade": _pn(dens_edit),
                        "umidade": _pn(umidade_edit),
                        "teste_filme": tf_edit,
                        "grade": grade_edit,
                        "cor": cor_edit,
                        "analista": analista_edit.strip(),
                        "observacao": obs_edit.strip(),
                    }
                    update_row_multi("qualidade", "id", analise_id, novos_valores)

                    st.success(f"Analise do lote **{lote_edit}** atualizada. Novo grade: **{grade_edit} - {cor_edit}**")
                    st.toast("Analise atualizada!")
                except Exception as exc:
                    st.error(f"Erro ao salvar: {exc}")


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
