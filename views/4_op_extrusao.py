import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, datetime

from utils.database import read_sheet, append_row, update_rows, read_sheet_no_cache, proximo_sequencial
from utils.formatters import EXTRUSORAS, formatar_peso, formatar_data, formatar_percentual

try:
    from utils.pdf_generator import gerar_pdf_op_extrusao
except ImportError:
    gerar_pdf_op_extrusao = None

st.title("OP Extrusao")

tab_nova, tab_consultar, tab_fechar = st.tabs(["Nova OP", "Consultar OPs", "Fechar OP"])

# ---------------------------------------------------------------------------
# Tab: Nova OP
# ---------------------------------------------------------------------------
with tab_nova:
    st.subheader("Criar Nova Ordem de Producao - Extrusao")

    numero_op = proximo_sequencial("op_extrusao", "numero_op", "OPE")
    st.info(f"Numero da OP: **{numero_op}**")

    col1, col2 = st.columns(2)
    with col1:
        data_op = st.date_input("Data", value=date.today(), key="ope_data")
        responsavel = st.text_input("Responsavel", key="ope_resp")
        cliente = st.text_input("Cliente", key="ope_cliente")
    with col2:
        origem = st.selectbox("Origem do Material", ["Proprio", "Servico"], key="ope_origem")
        produto = st.text_input("Produto", key="ope_prod")
        maquina = st.selectbox("Maquina", options=EXTRUSORAS, format_func=lambda x: f"Extrusora {x}", key="ope_maq")

    opl_vinculada = ""
    volume_ton = 0.0

    if origem == "Proprio":
        try:
            df_opl = read_sheet("op_lavacao")
            if not df_opl.empty:
                opls_disponiveis = df_opl["numero_op"].astype(str).tolist()
                opl_vinculada = st.selectbox(
                    "OPL de Origem (rastreabilidade)",
                    options=opls_disponiveis,
                    key="ope_opl_origem",
                )
                if opl_vinculada:
                    opl_row = df_opl[df_opl["numero_op"].astype(str) == opl_vinculada]
                    if not opl_row.empty:
                        volume_ton = float(opl_row.iloc[0].get("volume_ton", 0) or 0)
                        st.success(f"Volume puxado da OPL **{opl_vinculada}**: **{volume_ton:.2f} ton** ({volume_ton * 1000:,.1f} kg)")
            else:
                st.warning("Nenhuma OPL cadastrada.")
        except Exception:
            st.warning("Erro ao carregar OPLs.")
    aparas_servico_ids = []
    if origem == "Servico":
        st.info("Servico de industrializacao - selecione as aparas de servico.")
        try:
            df_aparas_serv = read_sheet("aparas_estoque")
            if not df_aparas_serv.empty and "tipo_material" in df_aparas_serv.columns:
                df_serv_disp = df_aparas_serv[
                    (df_aparas_serv["tipo_material"].astype(str) == "Servico")
                    & (df_aparas_serv["status"].astype(str) == "disponivel")
                ].copy()
                if df_serv_disp.empty:
                    st.warning("Nenhuma apara de Servico classificada e disponivel.")
                    volume_ton = st.number_input(
                        "Volume (ton) - manual", min_value=0.0, step=0.5, format="%.2f",
                        key="ope_vol_servico_manual", value=None,
                    ) or 0.0
                else:
                    df_serv_disp["peso_kg"] = pd.to_numeric(df_serv_disp["peso_kg"], errors="coerce").fillna(0)
                    df_serv_disp["selecionar"] = False
                    df_serv_view = df_serv_disp[
                        ["selecionar", "numero_nf", "fornecedor", "qualidade", "tipo_fardo", "quantidade", "peso_kg"]
                    ].copy()
                    edited_serv = st.data_editor(
                        df_serv_view, use_container_width=True, hide_index=True,
                        disabled=["numero_nf", "fornecedor", "qualidade", "tipo_fardo", "quantidade", "peso_kg"],
                        column_config={
                            "selecionar": st.column_config.CheckboxColumn("Selecionar"),
                            "numero_nf": "NF", "fornecedor": "Fornecedor",
                            "qualidade": "Qual.", "tipo_fardo": "Tipo",
                            "quantidade": "Qtd", "peso_kg": "Peso (kg)",
                        },
                        key="ope_serv_editor",
                    )
                    sel_serv = edited_serv[edited_serv["selecionar"] == True]
                    if not sel_serv.empty:
                        peso_sel = 0.0
                        for _, r in sel_serv.iterrows():
                            orig_r = df_serv_disp[df_serv_disp["numero_nf"].astype(str) == str(r["numero_nf"])].iloc[0]
                            aparas_servico_ids.append(str(orig_r["id"]))
                            peso_sel += float(orig_r["peso_kg"])
                        volume_ton = peso_sel / 1000
                        st.success(f"Volume das aparas selecionadas: **{volume_ton:.2f} ton** ({peso_sel:,.1f} kg)")
                    else:
                        volume_ton = 0.0
                        st.info("Selecione as aparas de servico marcando 'Selecionar'.")
            else:
                volume_ton = st.number_input(
                    "Volume (ton)", min_value=0.0, step=0.5, format="%.2f",
                    key="ope_vol_servico", value=None,
                ) or 0.0
        except Exception:
            volume_ton = st.number_input(
                "Volume (ton)", min_value=0.0, step=0.5, format="%.2f",
                key="ope_vol_servico_err", value=None,
            ) or 0.0

    col_ad1, col_ad2 = st.columns(2)
    with col_ad1:
        aditivo_percentual = st.number_input(
            "Aditivo (%)", min_value=0.0, max_value=100.0, step=0.1, value=None, format="%.1f",
            key="ope_aditivo_pct",
            help="Percentual de aditivo no material",
        )

    aditivo_kg_total = volume_ton * 1000 * ((aditivo_percentual or 0) / 100)
    perc_reciclado_op = 100 - (aditivo_percentual or 0)
    if (aditivo_percentual or 0) > 0 and volume_ton > 0:
        st.info(
            f"Aditivo total: **{aditivo_kg_total:,.1f} kg** "
            f"({(aditivo_percentual or 0):.1f}% de {volume_ton:.2f} ton)  \n"
            f"Conteudo reciclado: **{perc_reciclado_op:.1f}%**"
        )

    observacao = st.text_area("Observacao", key="ope_obs")

    if st.button("Criar OP", type="primary", use_container_width=True, key="ope_criar"):
        erros = []
        if not responsavel.strip():
            erros.append("Responsavel e obrigatorio.")
        if origem == "Proprio" and not opl_vinculada:
            erros.append("Selecione a OPL de origem.")
        if origem == "Servico" and (not volume_ton or volume_ton <= 0):
            erros.append("Informe o volume manualmente para OPE de servico.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            try:
                tipo_lote = "01" if origem == "Proprio" else "02"
                dados = {
                    "numero_op": numero_op.strip().upper(),
                    "data": data_op.isoformat(),
                    "responsavel": responsavel.strip(),
                    "cliente": cliente.strip(),
                    "volume_ton": float(volume_ton or 0),
                    "origem": origem,
                    "tipo_lote": tipo_lote,
                    "opl_origem": opl_vinculada if origem == "Proprio" else "",
                    "produto": produto.strip(),
                    "maquina": maquina,
                    "aditivo_percentual": float(aditivo_percentual or 0),
                    "aditivo_kg_total": float(aditivo_kg_total),
                    "data_inicio": "",
                    "data_final": "",
                    "coordenador": "",
                    "producao_final_kg": "",
                    "perda_percentual": "",
                    "status": "aberta",
                    "observacao": observacao.strip(),
                }
                append_row("op_extrusao", dados)
                if origem == "Servico" and aparas_servico_ids:
                    update_rows("aparas_estoque", "id", aparas_servico_ids, "status", "em_uso")
                    update_rows("aparas_estoque", "id", aparas_servico_ids, "opl_em_uso", numero_op.strip().upper())
                st.success(f"OP {numero_op.strip().upper()} criada com sucesso!")

                # Botao para baixar PDF da OP recem-criada
                if gerar_pdf_op_extrusao is not None:
                    try:
                        pdf_bytes = gerar_pdf_op_extrusao(dados, [])
                        st.download_button(
                            "Baixar PDF da OP",
                            pdf_bytes,
                            file_name=f"{numero_op.strip().upper()}.pdf",
                            mime="application/pdf",
                        )
                    except Exception:
                        pass
            except Exception as exc:
                st.error(f"Erro ao salvar OP: {exc}")

# ---------------------------------------------------------------------------
# Tab: Consultar OPs
# ---------------------------------------------------------------------------
with tab_consultar:
    st.subheader("Consultar Ordens de Producao - Extrusao")

    col_f1, col_f2 = st.columns(2)
    with col_f1:
        data_inicio = st.date_input("Data Inicio", value=date.today().replace(day=1), key="consulta_ini")
    with col_f2:
        data_fim = st.date_input("Data Fim", value=date.today(), key="consulta_fim")

    try:
        df_ops = read_sheet("op_extrusao")
    except Exception as exc:
        st.error(f"Erro ao carregar OPs: {exc}")
        df_ops = pd.DataFrame()

    if not df_ops.empty:
        df_ops["data_dt"] = pd.to_datetime(df_ops["data"], errors="coerce")
        mask = (df_ops["data_dt"] >= pd.Timestamp(data_inicio)) & (
            df_ops["data_dt"] <= pd.Timestamp(data_fim)
        )
        df_filtrado = df_ops[mask].copy()

        if df_filtrado.empty:
            st.info("Nenhuma OP encontrada no periodo selecionado.")
        else:
            colunas_exibir = [
                c for c in [
                    "numero_op", "data", "responsavel", "cliente",
                    "volume_ton", "produto", "maquina", "status",
                ] if c in df_filtrado.columns
            ]
            st.dataframe(
                df_filtrado[colunas_exibir].sort_values("data", ascending=False),
                use_container_width=True,
                hide_index=True,
            )

            # Show linked lots for each OP
            st.markdown("---")
            st.subheader("Lotes Vinculados")

            try:
                df_prod = read_sheet("producao_extrusao")
            except Exception:
                df_prod = pd.DataFrame()

            if not df_prod.empty:
                op_selecionada = st.selectbox(
                    "Selecione a OP para ver lotes",
                    options=df_filtrado["numero_op"].unique().tolist(),
                    key="consulta_op_lotes",
                )
                lotes_op = df_prod[df_prod["numero_op"] == op_selecionada]

                if lotes_op.empty:
                    st.info(f"Nenhum lote registrado para a OP {op_selecionada}.")
                else:
                    colunas_lote = [
                        c for c in [
                            "codigo_lote", "data", "turno", "extrusora",
                            "peso_kg", "status", "registrado_por",
                        ] if c in lotes_op.columns
                    ]
                    st.dataframe(
                        lotes_op[colunas_lote],
                        use_container_width=True,
                        hide_index=True,
                    )

                # Botao para baixar PDF da OP selecionada
                if gerar_pdf_op_extrusao is not None:
                    try:
                        op_row = df_filtrado[df_filtrado["numero_op"] == op_selecionada].iloc[0]
                        op_dict = op_row.to_dict()
                        lotes_lista = lotes_op.to_dict("records") if not lotes_op.empty else []
                        pdf_bytes = gerar_pdf_op_extrusao(op_dict, lotes_lista)
                        st.download_button(
                            "Baixar PDF da OP",
                            pdf_bytes,
                            file_name=f"{op_selecionada}.pdf",
                            mime="application/pdf",
                            key=f"pdf_op_ext_{op_selecionada}",
                        )
                    except Exception:
                        pass
            else:
                st.info("Nenhum lote de producao encontrado.")
    else:
        st.info("Nenhuma OP cadastrada.")

# ---------------------------------------------------------------------------
# Tab: Fechar OP
# ---------------------------------------------------------------------------
with tab_fechar:
    st.subheader("Fechar Ordem de Producao - Extrusao")

    try:
        df_ops_fechar = read_sheet("op_extrusao")
    except Exception as exc:
        st.error(f"Erro ao carregar OPs: {exc}")
        df_ops_fechar = pd.DataFrame()

    if not df_ops_fechar.empty and "status" in df_ops_fechar.columns:
        ops_abertas = df_ops_fechar[df_ops_fechar["status"] == "aberta"]

        if ops_abertas.empty:
            st.info("Nenhuma OP aberta para fechar.")
        else:
            op_sel = st.selectbox(
                "Selecione a OP",
                options=ops_abertas["numero_op"].tolist(),
                key="fechar_op_sel",
            )

            op_info = ops_abertas[ops_abertas["numero_op"] == op_sel].iloc[0]

            st.markdown("#### Resumo da OP")
            col_r1, col_r2, col_r3 = st.columns(3)
            with col_r1:
                st.metric("Cliente", op_info.get("cliente", "-"))
            with col_r2:
                st.metric("Produto", op_info.get("produto", "-"))
            with col_r3:
                st.metric("Volume Previsto", f"{op_info.get('volume_ton', 0)} ton")

            # Fetch linked production lots
            try:
                df_prod_fechar = read_sheet("producao_extrusao")
            except Exception:
                df_prod_fechar = pd.DataFrame()

            total_lotes = 0
            total_kg = 0.0
            if not df_prod_fechar.empty:
                lotes_vinculados = df_prod_fechar[df_prod_fechar["numero_op"] == op_sel]
                total_lotes = len(lotes_vinculados)
                if "peso_kg" in lotes_vinculados.columns:
                    total_kg = pd.to_numeric(
                        lotes_vinculados["peso_kg"], errors="coerce"
                    ).sum()

            col_m1, col_m2 = st.columns(2)
            with col_m1:
                st.metric("Lotes Produzidos", total_lotes)
            with col_m2:
                st.metric("Total Produzido", formatar_peso(total_kg))

            st.markdown("---")

            with st.form("form_fechar_op", clear_on_submit=False):
                producao_final_kg = st.number_input(
                    "Producao Final (kg)",
                    min_value=0.0,
                    value=None,
                    step=0.5,
                    format="%.1f",
                )
                perda_percentual = st.number_input(
                    "Perda (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1,
                    format="%.2f",
                    value=None,
                )

                fechar = st.form_submit_button(
                    "Fechar OP", use_container_width=True, type="primary"
                )

                if fechar:
                    try:
                        sp = __import__("utils.database", fromlist=["get_spreadsheet"]).get_spreadsheet()
                        ws = sp.worksheet("op_extrusao")
                        headers = ws.row_values(1)
                        all_data = ws.get_all_records()

                        for idx, row in enumerate(all_data, start=2):
                            if str(row.get("numero_op", "")) == str(op_sel):
                                if "status" in headers:
                                    ws.update_cell(idx, headers.index("status") + 1, "fechada")
                                if "producao_final_kg" in headers:
                                    ws.update_cell(
                                        idx,
                                        headers.index("producao_final_kg") + 1,
                                        float(producao_final_kg or 0),
                                    )
                                if "perda_percentual" in headers:
                                    ws.update_cell(
                                        idx,
                                        headers.index("perda_percentual") + 1,
                                        float(perda_percentual or 0),
                                    )
                                if "data_final" in headers:
                                    ws.update_cell(
                                        idx,
                                        headers.index("data_final") + 1,
                                        date.today().isoformat(),
                                    )
                                break

                        st.cache_data.clear()
                        st.success(
                            f"OP {op_sel} fechada com sucesso! "
                            f"Producao: {formatar_peso(float(producao_final_kg or 0))} | "
                            f"Perda: {formatar_percentual(float(perda_percentual or 0))}"
                        )
                    except Exception as exc:
                        st.error(f"Erro ao fechar OP: {exc}")
    else:
        st.info("Nenhuma OP cadastrada ou todas ja estao fechadas.")
