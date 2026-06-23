import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.database import read_sheet, read_sheet_no_cache, update_row_multi
from utils.formatters import formatar_data, formatar_peso, fardos_breakdown, formatar_fardos

# ---------------------------------------------------------------------------
# Titulo
# ---------------------------------------------------------------------------
st.header("Classificacao de Materia Prima")

tab_classificar, tab_historico = st.tabs(["Classificar NF", "Historico"])

# ===========================================================================
# Tab 1: Classificar NF
# ===========================================================================
with tab_classificar:
    st.subheader("Classificar NFs em aguardando classificacao")

    # Mensagem de sucesso persistente (sobrevive ao rerun apos classificar)
    if st.session_state.get("clf_msg_sucesso"):
        st.success(st.session_state["clf_msg_sucesso"])

    try:
        df_estoque = read_sheet_no_cache("aparas_estoque")
    except Exception as exc:
        st.error(f"Erro ao carregar estoque de aparas: {exc}")
        df_estoque = pd.DataFrame()

    if df_estoque.empty or "status" not in df_estoque.columns:
        st.info("Nenhuma NF aguardando classificacao.")
    else:
        df_aguardando = df_estoque[
            df_estoque["status"].astype(str) == "aguardando_classificacao"
        ].copy()

        if df_aguardando.empty:
            st.info("Nenhuma NF aguardando classificacao.")
        else:
            # Normalizar campos numericos
            df_aguardando["peso_kg"] = pd.to_numeric(
                df_aguardando["peso_kg"], errors="coerce"
            ).fillna(0)
            df_aguardando["quantidade"] = pd.to_numeric(
                df_aguardando["quantidade"], errors="coerce"
            ).fillna(0)

            # Tabela resumo
            df_aguardando["qtd_fardao"] = df_aguardando.apply(lambda r: fardos_breakdown(r)[0], axis=1)
            df_aguardando["qtd_fardinho"] = df_aguardando.apply(lambda r: fardos_breakdown(r)[1], axis=1)
            df_tabela = df_aguardando[
                [
                    "numero_nf",
                    "fornecedor",
                    "tipo_fardo",
                    "qtd_fardao",
                    "qtd_fardinho",
                    "quantidade",
                    "peso_kg",
                    "data_recebimento",
                ]
            ].copy()
            df_tabela["data_recebimento"] = df_tabela["data_recebimento"].apply(
                formatar_data
            )
            df_tabela["peso_kg"] = df_tabela["peso_kg"].apply(formatar_peso)

            st.dataframe(df_tabela, use_container_width=True, hide_index=True)

            st.divider()

            # ---------------------------------------------------------------
            # Selecao da NF para classificar
            # ---------------------------------------------------------------
            opcoes_map = {}
            for _, row in df_aguardando.iterrows():
                rotulo = (
                    f"NF {row.get('numero_nf', '')} - "
                    f"{row.get('fornecedor', '')} - "
                    f"{formatar_peso(float(row.get('peso_kg', 0) or 0))}"
                )
                opcoes_map[rotulo] = row["id"]

            opcoes = list(opcoes_map.keys())

            escolha = st.selectbox(
                "Selecione a NF para classificar",
                options=opcoes,
                index=0 if opcoes else None,
                key="clf_nf_selecionada",
            )

            if escolha:
                id_selecionado = opcoes_map[escolha]
                nf_row = df_aguardando[df_aguardando["id"] == id_selecionado].iloc[0]

                # Detalhes da NF
                st.markdown("#### Detalhes da NF")
                col_a, col_b, col_c = st.columns(3)
                with col_a:
                    st.metric("Numero NF", str(nf_row.get("numero_nf", "")))
                    st.metric("Fornecedor", str(nf_row.get("fornecedor", "")))
                with col_b:
                    st.metric("Tipo Fardo", str(nf_row.get("tipo_fardo", "")))
                    _fa, _fi = fardos_breakdown(nf_row)
                    st.metric(
                        "Fardos",
                        formatar_fardos(_fa, _fi),
                        help=f"Total: {int(float(nf_row.get('quantidade', 0) or 0))} fardos",
                    )
                with col_c:
                    st.metric(
                        "Peso",
                        formatar_peso(float(nf_row.get("peso_kg", 0) or 0)),
                    )
                    st.metric(
                        "Recebimento",
                        formatar_data(nf_row.get("data_recebimento", "")),
                    )

                obs_existente = str(nf_row.get("observacao", "") or "")
                if obs_existente:
                    st.caption(f"Observacao registrada: {obs_existente}")

                st.divider()

                # ---------------------------------------------------------------
                # Formulario de classificacao
                # ---------------------------------------------------------------
                with st.form("form_classificar_nf", clear_on_submit=False):
                    qualidade = st.radio(
                        "Qualidade",
                        options=["A", "B", "C"],
                        horizontal=True,
                        help=(
                            "A: melhor qualidade, baixa contaminacao | "
                            "B: intermediario | "
                            "C: mais contaminado"
                        ),
                        key="clf_qualidade",
                    )

                    st.caption(
                        "A: melhor qualidade, baixa contaminacao  \n"
                        "B: intermediario  \n"
                        "C: mais contaminado"
                    )

                    classificado_por = st.text_input(
                        "Classificado por *",
                        key="clf_classificado_por",
                    )

                    observacao_classificacao = st.text_area(
                        "Observacao da classificacao",
                        key="clf_observacao",
                    )

                    data_classificacao = st.date_input(
                        "Data da classificacao",
                        value=date.today(),
                        key="clf_data",
                    )

                    submitted = st.form_submit_button(
                        f"Classificar como Qualidade {qualidade}",
                        type="primary",
                    )

                    if submitted:
                        if not classificado_por.strip():
                            st.error("Informe o nome do responsavel pela classificacao.")
                        else:
                            try:
                                # Construir observacao final (anexa a existente)
                                partes_obs = []
                                if obs_existente.strip():
                                    partes_obs.append(obs_existente.strip())
                                if observacao_classificacao.strip():
                                    partes_obs.append(
                                        "[Classificacao] "
                                        + observacao_classificacao.strip()
                                    )
                                obs_final = " | ".join(partes_obs)

                                update_row_multi(
                                    "aparas_estoque",
                                    "id",
                                    id_selecionado,
                                    {
                                        "qualidade": qualidade,
                                        "status": "disponivel",
                                        "data_classificacao": data_classificacao.isoformat(),
                                        "classificado_por": classificado_por.strip(),
                                        "observacao": obs_final,
                                    },
                                )

                                st.session_state["clf_msg_sucesso"] = (
                                    f"NF {nf_row.get('numero_nf', '')} "
                                    f"classificada como Qualidade {qualidade}."
                                )
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Erro ao classificar NF: {exc}")

# ===========================================================================
# Tab 2: Historico
# ===========================================================================
with tab_historico:
    st.subheader("Historico de Classificacao")

    try:
        df_hist_full = read_sheet("aparas_estoque")
    except Exception as exc:
        st.error(f"Erro ao carregar historico: {exc}")
        df_hist_full = pd.DataFrame()

    if df_hist_full.empty or "status" not in df_hist_full.columns:
        st.info("Nenhuma NF classificada ate o momento.")
    else:
        df_hist = df_hist_full[
            df_hist_full["status"].astype(str) != "aguardando_classificacao"
        ].copy()

        if df_hist.empty:
            st.info("Nenhuma NF classificada ate o momento.")
        else:
            # Normalizar tipos
            df_hist["peso_kg"] = pd.to_numeric(
                df_hist["peso_kg"], errors="coerce"
            ).fillna(0)
            df_hist["quantidade"] = pd.to_numeric(
                df_hist["quantidade"], errors="coerce"
            ).fillna(0)
            df_hist["data_classificacao_dt"] = pd.to_datetime(
                df_hist["data_classificacao"], errors="coerce"
            ).dt.date
            df_hist["qualidade"] = df_hist["qualidade"].astype(str).str.upper()

            # ---------------------------------------------------------------
            # Filtros
            # ---------------------------------------------------------------
            col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
            with col_f1:
                data_ini = st.date_input(
                    "Data inicio",
                    value=date.today() - timedelta(days=30),
                    key="hist_data_ini",
                )
            with col_f2:
                data_fim = st.date_input(
                    "Data fim",
                    value=date.today(),
                    key="hist_data_fim",
                )
            with col_f3:
                filtro_qualidade = st.multiselect(
                    "Qualidade",
                    options=["A", "B", "C"],
                    default=["A", "B", "C"],
                    key="hist_filtro_qualidade",
                )

            df_view = df_hist.copy()

            # Filtrar por data (mantem linhas sem data fora do filtro de data)
            mask_data = df_view["data_classificacao_dt"].apply(
                lambda d: (d is not None)
                and (not pd.isna(d))
                and (data_ini <= d <= data_fim)
            )
            df_view = df_view[mask_data]

            if filtro_qualidade:
                df_view = df_view[df_view["qualidade"].isin(filtro_qualidade)]

            # ---------------------------------------------------------------
            # Resumo por qualidade
            # ---------------------------------------------------------------
            st.markdown("#### Resumo por Qualidade")
            col_qa, col_qb, col_qc = st.columns(3)

            def _resumo_qualidade(df_in: pd.DataFrame, letra: str):
                sub = df_in[df_in["qualidade"] == letra]
                qtd = len(sub)
                peso = sub["peso_kg"].sum()
                return qtd, peso

            qa, pa = _resumo_qualidade(df_view, "A")
            qb, pb = _resumo_qualidade(df_view, "B")
            qc, pc = _resumo_qualidade(df_view, "C")

            with col_qa:
                st.metric("Qualidade A - NFs", qa, formatar_peso(pa))
            with col_qb:
                st.metric("Qualidade B - NFs", qb, formatar_peso(pb))
            with col_qc:
                st.metric("Qualidade C - NFs", qc, formatar_peso(pc))

            st.divider()

            # ---------------------------------------------------------------
            # Tabela de historico
            # ---------------------------------------------------------------
            if df_view.empty:
                st.info("Nenhuma NF encontrada com os filtros selecionados.")
            else:
                df_view = df_view.sort_values(
                    "data_classificacao_dt", ascending=False
                )

                df_view["qtd_fardao"] = df_view.apply(lambda r: fardos_breakdown(r)[0], axis=1)
                df_view["qtd_fardinho"] = df_view.apply(lambda r: fardos_breakdown(r)[1], axis=1)
                colunas_exibir = [
                    "data_classificacao",
                    "numero_nf",
                    "fornecedor",
                    "tipo_fardo",
                    "qtd_fardao",
                    "qtd_fardinho",
                    "quantidade",
                    "peso_kg",
                    "qualidade",
                    "status",
                    "classificado_por",
                    "data_recebimento",
                    "observacao",
                ]
                colunas_exibir = [
                    c for c in colunas_exibir if c in df_view.columns
                ]

                df_show = df_view[colunas_exibir].copy()

                if "data_classificacao" in df_show.columns:
                    df_show["data_classificacao"] = df_show[
                        "data_classificacao"
                    ].apply(formatar_data)
                if "data_recebimento" in df_show.columns:
                    df_show["data_recebimento"] = df_show[
                        "data_recebimento"
                    ].apply(formatar_data)
                if "peso_kg" in df_show.columns:
                    df_show["peso_kg"] = df_show["peso_kg"].apply(formatar_peso)

                st.dataframe(
                    df_show, use_container_width=True, hide_index=True
                )

                total_nfs = len(df_view)
                total_peso = df_view["peso_kg"].sum()
                st.markdown(
                    f"**Total filtrado:** {total_nfs} NFs | "
                    f"{formatar_peso(total_peso)}"
                )
