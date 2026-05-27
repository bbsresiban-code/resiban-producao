import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.database import (
    read_sheet,
    read_sheet_no_cache,
    append_row,
    append_rows,
    update_rows,
    proximo_sequencial,
)
from utils.serial_code import gerar_codigo_serial
from utils.formatters import formatar_data, formatar_peso, EXTRUSORAS

# ---------------------------------------------------------------------------
# Controle de acesso - apenas master
# ---------------------------------------------------------------------------
perfil_logado = st.session_state.get("perfil", "master")
usuario_logado = st.session_state.get("usuario", "master")

if perfil_logado != "master":
    st.error("Acesso restrito. Apenas o perfil master pode acessar o modulo de Mistura.")
    st.stop()

# ---------------------------------------------------------------------------
# Titulo
# ---------------------------------------------------------------------------
st.header("Mistura - Silo Homogeneizador")

tab_nova, tab_consultar, tab_historico = st.tabs(
    ["Nova Mistura", "Consultar Misturas", "Historico"]
)

# ===========================================================================
# TAB: Nova Mistura
# ===========================================================================
with tab_nova:
    st.subheader("Criar Nova Mistura")

    # Numero sequencial da mistura
    numero_mistura = proximo_sequencial("mistura", "numero_mistura", "MIX")
    st.info(f"Numero da Mistura: **{numero_mistura}**")

    col_c1, col_c2 = st.columns(2)
    with col_c1:
        data_mistura = st.date_input("Data", value=date.today(), key="mix_data")
    with col_c2:
        extrusora = st.selectbox(
            "Extrusora de Destino",
            options=EXTRUSORAS,
            key="mix_extrusora",
        )

    st.divider()

    # -------------------------------------------------------------------
    # Selecao de lotes disponiveis
    # -------------------------------------------------------------------
    st.markdown("#### Selecionar Lotes para Mistura")

    try:
        df_ext = read_sheet_no_cache("producao_extrusao")
    except Exception as exc:
        st.error(f"Erro ao carregar lotes: {exc}")
        df_ext = pd.DataFrame()

    try:
        df_qual = read_sheet("qualidade")
    except Exception as exc:
        df_qual = pd.DataFrame()

    if df_ext.empty:
        st.info("Nenhum lote encontrado na base de producao.")
    else:
        df_disp = df_ext[df_ext["status"] == "disponivel"].copy()

        if df_disp.empty:
            st.info("Nenhum lote com status 'disponivel' encontrado.")
        else:
            df_disp["peso_kg"] = pd.to_numeric(
                df_disp["peso_kg"], errors="coerce"
            ).fillna(0)

            # Juntar com qualidade para exibir grade e cor
            if not df_qual.empty:
                df_qual_unico = df_qual.drop_duplicates(
                    subset="codigo_lote", keep="last"
                )
                df_lotes = df_disp.merge(
                    df_qual_unico[["codigo_lote", "grade", "cor"]],
                    on="codigo_lote",
                    how="left",
                )
            else:
                df_lotes = df_disp.copy()
                df_lotes["grade"] = ""
                df_lotes["cor"] = ""

            df_lotes["grade"] = df_lotes["grade"].fillna("")
            df_lotes["cor"] = df_lotes["cor"].fillna("")

            # Preparar dataframe para data_editor com coluna de selecao
            colunas_exibir = ["codigo_lote", "peso_kg", "grade", "cor", "data",
                              "extrusora", "opl_origem"]
            colunas_disponiveis = [c for c in colunas_exibir if c in df_lotes.columns]

            df_selecao = df_lotes[colunas_disponiveis].copy()
            df_selecao.insert(0, "selecionar", False)

            if "data" in df_selecao.columns:
                df_selecao["data"] = df_selecao["data"].apply(formatar_data)

            df_editado = st.data_editor(
                df_selecao,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "selecionar": st.column_config.CheckboxColumn(
                        "Selecionar", default=False
                    ),
                    "codigo_lote": st.column_config.TextColumn(
                        "Codigo Lote", disabled=True
                    ),
                    "peso_kg": st.column_config.NumberColumn(
                        "Peso (kg)", disabled=True, format="%.1f"
                    ),
                    "grade": st.column_config.TextColumn("Grade", disabled=True),
                    "cor": st.column_config.TextColumn("Cor", disabled=True),
                    "data": st.column_config.TextColumn("Data", disabled=True),
                    "extrusora": st.column_config.TextColumn(
                        "Extrusora", disabled=True
                    ),
                    "opl_origem": st.column_config.TextColumn(
                        "OPL Origem", disabled=True
                    ),
                },
                key="mix_selecao_lotes",
            )

            # Totais dos selecionados
            selecionados = df_editado[df_editado["selecionar"] == True]
            qtd_selecionados = len(selecionados)
            peso_total = (
                selecionados["peso_kg"].sum() if qtd_selecionados > 0 else 0.0
            )

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric("Lotes Selecionados", qtd_selecionados)
            with col_m2:
                st.metric("Peso Total da Mistura", formatar_peso(peso_total))

            st.divider()

            # -------------------------------------------------------------------
            # Botao de criacao da mistura
            # -------------------------------------------------------------------
            if st.button(
                "Criar Mistura", type="primary", use_container_width=True
            ):
                erros = []
                if qtd_selecionados < 2:
                    erros.append(
                        "Selecione pelo menos 2 lotes para criar uma mistura."
                    )

                if erros:
                    for e in erros:
                        st.error(e)
                else:
                    try:
                        # 1) Gerar codigo serial do novo lote de mistura (tipo 06)
                        codigo_lote_mistura, sequencial = gerar_codigo_serial(
                            "06", extrusora, data_mistura
                        )

                        # 2) Lista de codigos dos lotes de entrada
                        codigos_entrada = selecionados["codigo_lote"].tolist()
                        lotes_entrada_str = ", ".join(codigos_entrada)

                        # 3) Salvar registro na aba "mistura"
                        dados_mistura = {
                            "numero_mistura": numero_mistura,
                            "data": data_mistura.isoformat(),
                            "codigo_lote_mistura": codigo_lote_mistura,
                            "extrusora": extrusora,
                            "peso_total_kg": peso_total,
                            "qtd_lotes": qtd_selecionados,
                            "lotes_entrada": lotes_entrada_str,
                            "registrado_por": usuario_logado,
                            "status": "em_analise",
                        }
                        append_row("mistura", dados_mistura)

                        # 4) Criar novo lote na producao_extrusao
                        dados_lote = {
                            "data": data_mistura.isoformat(),
                            "turno": "",
                            "hora": "",
                            "numero_op": "",
                            "opl_origem": "",
                            "codigo_lote": codigo_lote_mistura,
                            "tipo": "06",
                            "tipo_descricao": "Mistura",
                            "extrusora": extrusora,
                            "peso_kg": peso_total,
                            "mes": data_mistura.month,
                            "ano": data_mistura.year % 100,
                            "sequencial": sequencial,
                            "status": "em_analise",
                            "observacao_lote": f"Mistura {numero_mistura} - {qtd_selecionados} lotes",
                            "registrado_por": usuario_logado,
                        }
                        append_row("producao_extrusao", dados_lote)

                        # 5) Atualizar status dos lotes de entrada para "misturado"
                        update_rows(
                            "producao_extrusao",
                            match_col="codigo_lote",
                            match_values=codigos_entrada,
                            update_col="status",
                            new_value="misturado",
                        )

                        st.toast("Mistura criada com sucesso!")
                        st.success(
                            f"Mistura criada com sucesso!  \n"
                            f"### Lote de Mistura: `{codigo_lote_mistura}`  \n"
                            f"**Mistura:** {numero_mistura}  \n"
                            f"**Lotes combinados:** {qtd_selecionados}  \n"
                            f"**Peso total:** {formatar_peso(peso_total)}"
                        )
                        st.balloons()

                    except Exception as exc:
                        st.error(f"Erro ao criar mistura: {exc}")

# ===========================================================================
# TAB: Consultar Misturas
# ===========================================================================
with tab_consultar:
    st.subheader("Consultar Misturas")

    try:
        df_mix = read_sheet("mistura")
    except Exception as exc:
        st.error(f"Erro ao carregar misturas: {exc}")
        df_mix = pd.DataFrame()

    if df_mix.empty:
        st.info("Nenhuma mistura encontrada.")
    else:
        df_mix["peso_total_kg"] = pd.to_numeric(
            df_mix["peso_total_kg"], errors="coerce"
        ).fillna(0)
        df_mix["qtd_lotes"] = pd.to_numeric(
            df_mix["qtd_lotes"], errors="coerce"
        ).fillna(0).astype(int)

        colunas_consulta = [
            c for c in [
                "numero_mistura", "data", "codigo_lote_mistura",
                "peso_total_kg", "qtd_lotes", "status",
            ] if c in df_mix.columns
        ]

        df_mix_exibir = df_mix[colunas_consulta].copy()

        if "data" in df_mix_exibir.columns:
            df_mix_exibir["data"] = df_mix_exibir["data"].apply(formatar_data)

        st.dataframe(
            df_mix_exibir,
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            f"Total: {len(df_mix_exibir)} misturas | "
            f"{formatar_peso(df_mix['peso_total_kg'].sum())}"
        )

        # Detalhes expandiveis
        st.divider()
        st.markdown("#### Detalhes das Misturas")

        for _, row in df_mix.iterrows():
            label = (
                f"{formatar_data(row.get('data', ''))} | "
                f"{row.get('numero_mistura', '')} | "
                f"Lote: {row.get('codigo_lote_mistura', '')} | "
                f"{formatar_peso(float(row.get('peso_total_kg', 0)))} | "
                f"Status: {row.get('status', '')}"
            )
            with st.expander(label):
                col_d1, col_d2 = st.columns(2)
                with col_d1:
                    st.markdown(f"**Mistura:** {row.get('numero_mistura', '')}")
                    st.markdown(
                        f"**Codigo do Lote:** `{row.get('codigo_lote_mistura', '')}`"
                    )
                    st.markdown(f"**Extrusora:** {row.get('extrusora', '')}")
                    st.markdown(
                        f"**Peso Total:** {formatar_peso(float(row.get('peso_total_kg', 0)))}"
                    )
                with col_d2:
                    st.markdown(f"**Qtd Lotes:** {row.get('qtd_lotes', '')}")
                    st.markdown(f"**Status:** {row.get('status', '')}")
                    st.markdown(
                        f"**Registrado Por:** {row.get('registrado_por', '')}"
                    )
                    st.markdown(
                        f"**Data:** {formatar_data(row.get('data', ''))}"
                    )

                # Listar lotes de entrada
                lotes_entrada = str(row.get("lotes_entrada", ""))
                if lotes_entrada:
                    st.markdown("**Lotes de Entrada:**")
                    lotes_lista = [
                        lt.strip() for lt in lotes_entrada.split(",") if lt.strip()
                    ]
                    for lt in lotes_lista:
                        st.markdown(f"- `{lt}`")

# ===========================================================================
# TAB: Historico
# ===========================================================================
with tab_historico:
    st.subheader("Historico de Misturas")

    col_fh1, col_fh2 = st.columns(2)
    with col_fh1:
        hist_data_inicio = st.date_input(
            "Data Inicio",
            value=date.today() - timedelta(days=30),
            key="mix_hist_inicio",
        )
    with col_fh2:
        hist_data_fim = st.date_input(
            "Data Fim", value=date.today(), key="mix_hist_fim"
        )

    try:
        df_hist = read_sheet("mistura")
    except Exception as exc:
        st.error(f"Erro ao carregar historico: {exc}")
        df_hist = pd.DataFrame()

    if df_hist.empty:
        st.info("Nenhuma mistura encontrada.")
    else:
        df_hist["data_dt"] = pd.to_datetime(
            df_hist["data"], errors="coerce"
        ).dt.date
        df_hist["peso_total_kg"] = pd.to_numeric(
            df_hist["peso_total_kg"], errors="coerce"
        ).fillna(0)
        df_hist["qtd_lotes"] = pd.to_numeric(
            df_hist["qtd_lotes"], errors="coerce"
        ).fillna(0).astype(int)

        mask = (df_hist["data_dt"] >= hist_data_inicio) & (
            df_hist["data_dt"] <= hist_data_fim
        )
        df_filtrado = df_hist[mask].copy()

        if df_filtrado.empty:
            st.info("Nenhuma mistura encontrada no periodo selecionado.")
        else:
            df_filtrado = df_filtrado.sort_values("data_dt", ascending=False)

            colunas_hist = [
                c for c in [
                    "numero_mistura", "data", "codigo_lote_mistura",
                    "extrusora", "peso_total_kg", "qtd_lotes",
                    "lotes_entrada", "registrado_por", "status",
                ] if c in df_filtrado.columns
            ]

            df_hist_exibir = df_filtrado[colunas_hist].copy()

            if "data" in df_hist_exibir.columns:
                df_hist_exibir["data"] = df_hist_exibir["data"].apply(formatar_data)

            st.dataframe(
                df_hist_exibir,
                use_container_width=True,
                hide_index=True,
            )

            # Resumo do periodo
            st.markdown("---")
            st.subheader("Resumo do Periodo")

            total_misturas = len(df_filtrado)
            total_kg = df_filtrado["peso_total_kg"].sum()
            total_lotes_usados = df_filtrado["qtd_lotes"].sum()

            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Total de Misturas", total_misturas)
            with col_r2:
                st.metric("Peso Total", formatar_peso(total_kg))
            with col_r3:
                st.metric("Lotes Utilizados", int(total_lotes_usados))
