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
)
from utils.formatters import formatar_data, formatar_peso

# ---------------------------------------------------------------------------
# Titulo
# ---------------------------------------------------------------------------
st.header("Romaneio de Carregamento")

tab_novo, tab_historico = st.tabs(["Novo Romaneio", "Historico"])

# ===========================================================================
# TAB: Novo Romaneio
# ===========================================================================
with tab_novo:
    st.subheader("Criar Romaneio de Carregamento")

    # -------------------------------------------------------------------
    # Cabecalho do romaneio (fora do form para usar session_state)
    # -------------------------------------------------------------------
    st.markdown("#### Dados do Carregamento")

    col_h1, col_h2 = st.columns(2)
    with col_h1:
        rom_data = st.date_input("Data", value=date.today(), key="rom_data")
        rom_numero_pedido = st.text_input("Numero do Pedido", key="rom_numero_pedido")
        rom_cliente = st.text_input("Cliente", key="rom_cliente")
        rom_transportadora = st.text_input("Transportadora", key="rom_transportadora")
    with col_h2:
        rom_placa = st.text_input("Placa do Veiculo", key="rom_placa")
        rom_motorista = st.text_input("Motorista", key="rom_motorista")
        rom_responsavel = st.text_input(
            "Responsavel pelo Carregamento", key="rom_responsavel"
        )

    st.divider()

    # -------------------------------------------------------------------
    # Selecao de lotes disponiveis
    # -------------------------------------------------------------------
    st.markdown("#### Selecao de Lotes")

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
        st.info("Nenhum lote encontrado.")
    else:
        df_disp = df_ext[df_ext["status"] == "disponivel"].copy()

        if df_disp.empty:
            st.info("Nenhum lote disponivel para carregamento.")
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
            df_selecao = df_lotes[
                ["codigo_lote", "data", "tipo_descricao", "extrusora", "peso_kg", "grade", "cor"]
            ].copy()
            df_selecao.insert(0, "selecionar", False)
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
                    "data": st.column_config.TextColumn("Data", disabled=True),
                    "tipo_descricao": st.column_config.TextColumn(
                        "Tipo", disabled=True
                    ),
                    "extrusora": st.column_config.TextColumn(
                        "Extrusora", disabled=True
                    ),
                    "peso_kg": st.column_config.NumberColumn(
                        "Peso (kg)", disabled=True, format="%.1f"
                    ),
                    "grade": st.column_config.TextColumn("Grade", disabled=True),
                    "cor": st.column_config.TextColumn("Cor", disabled=True),
                },
                key="rom_selecao_lotes",
            )

            # Totais dos selecionados
            selecionados = df_editado[df_editado["selecionar"] == True]
            qtd_selecionados = len(selecionados)
            peso_selecionado = selecionados["peso_kg"].sum() if qtd_selecionados > 0 else 0.0

            col_t1, col_t2 = st.columns(2)
            with col_t1:
                st.metric("Lotes Selecionados", qtd_selecionados)
            with col_t2:
                st.metric("Peso Total Selecionado", formatar_peso(peso_selecionado))

            st.divider()

            # -------------------------------------------------------------------
            # Campos de fechamento
            # -------------------------------------------------------------------
            st.markdown("#### Fechamento")

            col_c1, col_c2 = st.columns(2)
            with col_c1:
                rom_nf_saida = st.text_input("NF de Saida", key="rom_nf_saida")
                rom_codigo_produto_nf = st.text_input(
                    "Codigo Produto NF", key="rom_codigo_produto_nf"
                )
            with col_c2:
                rom_serial = st.text_input("Serial", key="rom_serial")
                rom_registrado_por = st.text_input(
                    "Registrado Por", key="rom_registrado_por"
                )

            st.divider()

            # -------------------------------------------------------------------
            # Botao de envio
            # -------------------------------------------------------------------
            if st.button(
                "Finalizar Romaneio", type="primary", use_container_width=True
            ):
                erros = []
                if not rom_cliente.strip():
                    erros.append("Cliente e obrigatorio.")
                if not rom_responsavel.strip():
                    erros.append("Responsavel pelo carregamento e obrigatorio.")
                if qtd_selecionados == 0:
                    erros.append("Selecione pelo menos 1 lote.")
                if not rom_registrado_por.strip():
                    erros.append("Registrado Por e obrigatorio.")

                if erros:
                    for e in erros:
                        st.error(e)
                else:
                    try:
                        # 1) Criar registro do romaneio
                        romaneio_data = {
                            "data": rom_data.isoformat(),
                            "numero_pedido": rom_numero_pedido.strip(),
                            "cliente": rom_cliente.strip(),
                            "transportadora": rom_transportadora.strip(),
                            "placa_veiculo": rom_placa.strip(),
                            "motorista": rom_motorista.strip(),
                            "responsavel_carregamento": rom_responsavel.strip(),
                            "nf_saida": rom_nf_saida.strip(),
                            "codigo_produto_nf": rom_codigo_produto_nf.strip(),
                            "peso_total_kg": peso_selecionado,
                            "qtd_lotes": qtd_selecionados,
                            "serial": rom_serial.strip(),
                            "registrado_por": rom_registrado_por.strip(),
                        }
                        resultado_rom = append_row("romaneio", romaneio_data)
                        romaneio_id = resultado_rom["id"]

                        # 2) Criar itens do romaneio
                        codigos_selecionados = selecionados["codigo_lote"].tolist()
                        itens = []
                        for _, lote_row in selecionados.iterrows():
                            produto_desc = (
                                f"{lote_row.get('grade', '')} - {lote_row.get('cor', '')}"
                                if lote_row.get("grade")
                                else lote_row.get("tipo_descricao", "")
                            )
                            itens.append(
                                {
                                    "romaneio_id": romaneio_id,
                                    "codigo_lote": lote_row["codigo_lote"],
                                    "produto": produto_desc,
                                    "peso_kg": lote_row["peso_kg"],
                                }
                            )
                        append_rows("romaneio_itens", itens)

                        # 3) Atualizar status dos lotes para carregado
                        update_rows(
                            "producao_extrusao",
                            match_col="codigo_lote",
                            match_values=codigos_selecionados,
                            update_col="status",
                            new_value="carregado",
                        )

                        st.toast("Romaneio criado com sucesso!")
                        st.success(
                            f"Romaneio registrado com sucesso! "
                            f"{qtd_selecionados} lotes | "
                            f"{formatar_peso(peso_selecionado)} | "
                            f"ID: `{romaneio_id}`"
                        )
                    except Exception as exc:
                        st.error(f"Erro ao criar romaneio: {exc}")


# ===========================================================================
# TAB: Historico
# ===========================================================================
with tab_historico:
    st.subheader("Historico de Romaneios")

    col_fh1, col_fh2, col_fh3 = st.columns(3)
    with col_fh1:
        hist_data_inicio = st.date_input(
            "Data Inicio",
            value=date.today() - timedelta(days=30),
            key="rom_hist_inicio",
        )
    with col_fh2:
        hist_data_fim = st.date_input(
            "Data Fim", value=date.today(), key="rom_hist_fim"
        )
    with col_fh3:
        hist_cliente = st.text_input("Filtrar por Cliente", key="rom_hist_cliente")

    try:
        df_rom = read_sheet("romaneio")
    except Exception as exc:
        st.error(f"Erro ao carregar romaneios: {exc}")
        df_rom = pd.DataFrame()

    try:
        df_rom_itens = read_sheet("romaneio_itens")
    except Exception as exc:
        df_rom_itens = pd.DataFrame()

    if df_rom.empty:
        st.info("Nenhum romaneio encontrado.")
    else:
        df_rom["data_dt"] = pd.to_datetime(df_rom["data"], errors="coerce").dt.date
        df_rom["peso_total_kg"] = pd.to_numeric(
            df_rom["peso_total_kg"], errors="coerce"
        ).fillna(0)
        df_rom["qtd_lotes"] = pd.to_numeric(
            df_rom["qtd_lotes"], errors="coerce"
        ).fillna(0).astype(int)

        mask = (df_rom["data_dt"] >= hist_data_inicio) & (
            df_rom["data_dt"] <= hist_data_fim
        )
        df_rom_filtrado = df_rom[mask].copy()

        if hist_cliente.strip():
            df_rom_filtrado = df_rom_filtrado[
                df_rom_filtrado["cliente"]
                .str.lower()
                .str.contains(hist_cliente.strip().lower(), na=False)
            ]

        if df_rom_filtrado.empty:
            st.info("Nenhum romaneio encontrado no periodo selecionado.")
        else:
            df_rom_filtrado = df_rom_filtrado.sort_values("data_dt", ascending=False)

            st.dataframe(
                df_rom_filtrado[
                    [
                        "data",
                        "numero_pedido",
                        "cliente",
                        "transportadora",
                        "placa_veiculo",
                        "motorista",
                        "peso_total_kg",
                        "qtd_lotes",
                        "nf_saida",
                        "serial",
                    ]
                ].copy(),
                use_container_width=True,
                hide_index=True,
            )

            st.caption(
                f"Total: {len(df_rom_filtrado)} romaneios | "
                f"{formatar_peso(df_rom_filtrado['peso_total_kg'].sum())}"
            )

            # Detalhes expandiveis
            st.divider()
            st.markdown("#### Detalhes dos Romaneios")

            for _, row in df_rom_filtrado.iterrows():
                label = (
                    f"{formatar_data(row['data'])} | "
                    f"{row['cliente']} | "
                    f"Pedido: {row['numero_pedido']} | "
                    f"{formatar_peso(row['peso_total_kg'])}"
                )
                with st.expander(label):
                    col_d1, col_d2, col_d3 = st.columns(3)
                    with col_d1:
                        st.markdown(f"**Cliente:** {row['cliente']}")
                        st.markdown(f"**Pedido:** {row['numero_pedido']}")
                        st.markdown(f"**NF Saida:** {row.get('nf_saida', '')}")
                    with col_d2:
                        st.markdown(f"**Transportadora:** {row['transportadora']}")
                        st.markdown(f"**Placa:** {row['placa_veiculo']}")
                        st.markdown(f"**Motorista:** {row['motorista']}")
                    with col_d3:
                        st.markdown(
                            f"**Responsavel:** {row['responsavel_carregamento']}"
                        )
                        st.markdown(f"**Serial:** {row.get('serial', '')}")
                        st.markdown(
                            f"**Registrado Por:** {row.get('registrado_por', '')}"
                        )

                    # Itens do romaneio
                    if not df_rom_itens.empty:
                        itens_rom = df_rom_itens[
                            df_rom_itens["romaneio_id"] == row["id"]
                        ]
                        if not itens_rom.empty:
                            itens_rom_exibir = itens_rom[
                                ["codigo_lote", "produto", "peso_kg"]
                            ].copy()
                            itens_rom_exibir["peso_kg"] = pd.to_numeric(
                                itens_rom_exibir["peso_kg"], errors="coerce"
                            ).fillna(0)
                            st.caption("Lotes carregados:")
                            st.dataframe(
                                itens_rom_exibir,
                                use_container_width=True,
                                hide_index=True,
                            )
                            st.markdown(
                                f"**Total:** {len(itens_rom_exibir)} lotes | "
                                f"{formatar_peso(itens_rom_exibir['peso_kg'].sum())}"
                            )
                        else:
                            st.caption("Nenhum item encontrado para este romaneio.")
                    else:
                        st.caption("Nenhum item encontrado para este romaneio.")
