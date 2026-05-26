import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, timedelta

from utils.database import read_sheet, read_sheet_no_cache, append_row, update_rows, proximo_sequencial
from utils.formatters import formatar_data, formatar_peso

try:
    from utils.pdf_generator import gerar_pdf_op_lavacao
except ImportError:
    gerar_pdf_op_lavacao = None

st.header("Ordem de Producao - Lavacao")

tab_nova, tab_editar, tab_acompanhamento, tab_consultar = st.tabs(["Nova OP", "Editar OP", "Acompanhamento", "Consultar OPs"])

# ===========================================================================
# TAB 1: Nova OP
# ===========================================================================
with tab_nova:
    st.subheader("Criar nova Ordem de Producao")

    numero_op = proximo_sequencial("op_lavacao", "numero_op", "OPL")
    st.info(f"Numero da OP: **{numero_op}**")

    col1, col2 = st.columns(2)
    with col1:
        data_op = st.date_input("Data", value=date.today(), key="op_lav_data")
        responsavel = st.text_input("Responsavel", key="op_lav_resp")
        cliente = st.text_input("Cliente", key="op_lav_cliente")
    with col2:
        volume_ton = st.number_input("Volume (ton)", min_value=0.0, step=0.5, format="%.1f", key="op_lav_vol")
        produto = st.text_input("Produto", key="op_lav_prod")
        indice_fluidez = st.text_input("Indice de Fluidez", key="op_lav_mfi")

    observacao = st.text_area("Observacao", key="op_lav_obs")

    # -----------------------------------------------------------------------
    # Secao: NFs da OP
    # -----------------------------------------------------------------------
    st.divider()
    st.subheader("Notas Fiscais de Apara")
    st.caption("Adicione as NFs que serao consumidas nesta OP antes de criar.")

    if "nfs_temp" not in st.session_state:
        st.session_state.nfs_temp = []

    with st.form("form_add_nf", clear_on_submit=True):
        col_nf1, col_nf2, col_nf3 = st.columns(3)
        with col_nf1:
            nf_apara = st.text_input("NF Apara")
            fornecedor = st.text_input("Fornecedor")
        with col_nf2:
            tipo_fardo = st.selectbox("Tipo de Fardo", ["Fardinho", "Fardao"])
            quant_fardos = st.number_input("Quantidade de Fardos", min_value=0, step=1)
        with col_nf3:
            peso_kg = st.number_input("Peso (kg)", min_value=0.0, step=0.5, format="%.1f")
            obs_nf = st.text_input("Observacao da NF")

        add_nf = st.form_submit_button("Adicionar NF a lista", use_container_width=True)

    if add_nf:
        erros_nf = []
        if not nf_apara.strip():
            erros_nf.append("NF Apara e obrigatoria.")
        if quant_fardos <= 0:
            erros_nf.append("Quantidade de fardos deve ser maior que zero.")
        if peso_kg <= 0:
            erros_nf.append("Peso deve ser maior que zero.")

        if erros_nf:
            for e in erros_nf:
                st.error(e)
        else:
            st.session_state.nfs_temp.append({
                "nf_apara": nf_apara.strip(),
                "fornecedor": fornecedor.strip(),
                "tipo_fardo": tipo_fardo,
                "quant_fardos": quant_fardos,
                "peso_kg": peso_kg,
                "obs": obs_nf.strip(),
            })
            st.toast(f"NF {nf_apara} adicionada a lista!")
            st.rerun()

    if st.session_state.nfs_temp:
        df_nfs_temp = pd.DataFrame(st.session_state.nfs_temp)
        st.dataframe(
            df_nfs_temp[["nf_apara", "fornecedor", "tipo_fardo", "quant_fardos", "peso_kg", "obs"]],
            use_container_width=True,
            hide_index=True,
            column_config={
                "nf_apara": "NF Apara",
                "fornecedor": "Fornecedor",
                "tipo_fardo": "Tipo",
                "quant_fardos": "Qtd Fardos",
                "peso_kg": "Peso (kg)",
                "obs": "Obs",
            },
        )
        peso_total = sum(nf["peso_kg"] for nf in st.session_state.nfs_temp)
        total_fardos = sum(nf["quant_fardos"] for nf in st.session_state.nfs_temp)
        col_t1, col_t2, col_t3 = st.columns(3)
        col_t1.metric("NFs adicionadas", len(st.session_state.nfs_temp))
        col_t2.metric("Total Fardos", total_fardos)
        col_t3.metric("Peso Total", formatar_peso(peso_total))

        if st.button("Limpar lista de NFs"):
            st.session_state.nfs_temp = []
            st.rerun()
    else:
        st.warning("Nenhuma NF adicionada ainda. Adicione pelo menos uma NF antes de criar a OP.")

    # -----------------------------------------------------------------------
    # Botao: Criar OP
    # -----------------------------------------------------------------------
    st.divider()
    if st.button("Criar OP", type="primary", use_container_width=True):
        erros = []
        if not responsavel.strip():
            erros.append("Responsavel e obrigatorio.")
        if not cliente.strip():
            erros.append("Cliente e obrigatorio.")
        if volume_ton <= 0:
            erros.append("Volume deve ser maior que zero.")
        if not st.session_state.nfs_temp:
            erros.append("Adicione pelo menos uma NF antes de criar a OP.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            try:
                op_data = {
                    "numero_op": numero_op,
                    "data": data_op.isoformat(),
                    "responsavel": responsavel.strip(),
                    "cliente": cliente.strip(),
                    "volume_ton": volume_ton,
                    "produto": produto.strip(),
                    "indice_fluidez": indice_fluidez.strip(),
                    "status": "aberta",
                    "observacao": observacao.strip(),
                }
                resultado = append_row("op_lavacao", op_data)
                op_id = resultado["id"]

                nfs_salvas = []
                for nf in st.session_state.nfs_temp:
                    nf_data = {
                        "op_lavacao_id": op_id,
                        "nf_apara": nf["nf_apara"],
                        "fornecedor": nf["fornecedor"],
                        "tipo_fardo": nf["tipo_fardo"],
                        "quant_fardos": nf["quant_fardos"],
                        "peso_kg": nf["peso_kg"],
                        "obs": nf["obs"],
                    }
                    append_row("op_lavacao_nfs", nf_data)
                    nfs_salvas.append(nf_data)

                st.session_state.nfs_temp = []
                st.toast("OP criada com sucesso!")
                st.success(f"OP **{numero_op}** criada com {len(nfs_salvas)} NFs vinculadas!")

                if gerar_pdf_op_lavacao is not None:
                    try:
                        pdf_bytes = gerar_pdf_op_lavacao(op_data, nfs_salvas)
                        st.download_button(
                            "Baixar PDF da OP",
                            pdf_bytes,
                            file_name=f"{numero_op}.pdf",
                            mime="application/pdf",
                        )
                    except Exception:
                        pass
            except Exception as exc:
                st.error(f"Erro ao criar OP: {exc}")

# ===========================================================================
# TAB 2: Editar OP (adicionar NFs)
# ===========================================================================
with tab_editar:
    st.subheader("Adicionar NFs a uma OP existente")

    try:
        df_ops_edit = read_sheet_no_cache("op_lavacao")
    except Exception:
        df_ops_edit = pd.DataFrame()

    if df_ops_edit.empty:
        st.info("Nenhuma OP cadastrada.")
    else:
        ops_abertas_edit = df_ops_edit[df_ops_edit["status"].astype(str).str.lower() == "aberta"]
        if ops_abertas_edit.empty:
            st.info("Nenhuma OP aberta para editar.")
        else:
            opcoes_edit = ops_abertas_edit.apply(
                lambda r: f"{r['numero_op']} - {r['cliente']} ({formatar_data(r['data'])})", axis=1
            ).tolist()
            op_edit_label = st.selectbox("Selecione a OP", opcoes_edit, key="edit_op_sel")

            if op_edit_label:
                idx_edit = opcoes_edit.index(op_edit_label)
                op_edit = ops_abertas_edit.iloc[idx_edit]
                op_edit_id = op_edit["id"]
                op_edit_num = op_edit["numero_op"]

                st.markdown(f"**OP:** {op_edit_num} | **Cliente:** {op_edit['cliente']} | **Volume:** {op_edit['volume_ton']} ton")

                try:
                    df_nfs_edit = read_sheet_no_cache("op_lavacao_nfs")
                    if not df_nfs_edit.empty:
                        nfs_edit = df_nfs_edit[df_nfs_edit["op_lavacao_id"].astype(str) == str(op_edit_id)]
                    else:
                        nfs_edit = pd.DataFrame()
                except Exception:
                    nfs_edit = pd.DataFrame()

                if not nfs_edit.empty:
                    st.caption("NFs ja cadastradas:")
                    cols_show = ["nf_apara", "fornecedor", "tipo_fardo", "quant_fardos", "peso_kg", "obs"]
                    cols_ok = [c for c in cols_show if c in nfs_edit.columns]
                    st.dataframe(nfs_edit[cols_ok], use_container_width=True, hide_index=True)

                st.divider()
                st.subheader("Adicionar nova NF")

                with st.form("form_edit_nf", clear_on_submit=True):
                    col_e1, col_e2, col_e3 = st.columns(3)
                    with col_e1:
                        edit_nf = st.text_input("NF Apara", key="edit_nf_apara")
                        edit_fornec = st.text_input("Fornecedor", key="edit_fornec")
                    with col_e2:
                        edit_tipo = st.selectbox("Tipo de Fardo", ["Fardinho", "Fardao"], key="edit_tipo")
                        edit_qtd = st.number_input("Quantidade de Fardos", min_value=0, step=1, key="edit_qtd")
                    with col_e3:
                        edit_peso = st.number_input("Peso (kg)", min_value=0.0, step=0.5, format="%.1f", key="edit_peso")
                        edit_obs = st.text_input("Observacao", key="edit_obs")

                    edit_submit = st.form_submit_button("Adicionar NF", type="primary", use_container_width=True)

                if edit_submit:
                    erros_edit = []
                    if not edit_nf.strip():
                        erros_edit.append("NF Apara e obrigatoria.")
                    if edit_qtd <= 0:
                        erros_edit.append("Quantidade deve ser maior que zero.")
                    if edit_peso <= 0:
                        erros_edit.append("Peso deve ser maior que zero.")

                    if erros_edit:
                        for e in erros_edit:
                            st.error(e)
                    else:
                        try:
                            nf_nova = {
                                "op_lavacao_id": str(op_edit_id),
                                "nf_apara": edit_nf.strip(),
                                "fornecedor": edit_fornec.strip(),
                                "tipo_fardo": edit_tipo,
                                "quant_fardos": edit_qtd,
                                "peso_kg": edit_peso,
                                "obs": edit_obs.strip(),
                            }
                            append_row("op_lavacao_nfs", nf_nova)
                            st.toast("NF adicionada com sucesso!")
                            st.success(f"NF **{edit_nf}** adicionada a OP **{op_edit_num}**.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erro ao adicionar NF: {exc}")

# ===========================================================================
# TAB 3: Acompanhamento
# ===========================================================================
with tab_acompanhamento:
    st.subheader("Acompanhamento de OP em Andamento")

    try:
        df_ops_acomp = read_sheet_no_cache("op_lavacao")
    except Exception:
        df_ops_acomp = pd.DataFrame()

    if df_ops_acomp.empty:
        st.info("Nenhuma OP cadastrada.")
    else:
        ops_abertas = df_ops_acomp[df_ops_acomp["status"] == "aberta"].copy()

        if ops_abertas.empty:
            st.info("Nenhuma OP com status 'aberta' encontrada.")
        else:
            opcoes_ops = ops_abertas.apply(
                lambda r: f"{r['numero_op']} - {r['cliente']} ({formatar_data(r['data'])})", axis=1
            ).tolist()

            op_selecionada_label = st.selectbox("Selecione a OP", opcoes_ops, key="acomp_op_sel")

            if op_selecionada_label:
                idx_sel = opcoes_ops.index(op_selecionada_label)
                op_sel = ops_abertas.iloc[idx_sel]
                op_id_sel = op_sel["id"]
                numero_op_sel = op_sel["numero_op"]

                st.markdown(f"**OP:** {numero_op_sel} | **Cliente:** {op_sel['cliente']} | **Volume:** {op_sel['volume_ton']} ton | **Produto:** {op_sel['produto']}")

                # Carregar NFs da OP
                try:
                    df_nfs_acomp = read_sheet_no_cache("op_lavacao_nfs")
                except Exception:
                    df_nfs_acomp = pd.DataFrame()

                # Carregar producao lavacao
                try:
                    df_prod = read_sheet_no_cache("producao_lavacao")
                except Exception:
                    df_prod = pd.DataFrame()

                if df_nfs_acomp.empty:
                    st.warning("Nenhuma NF encontrada para esta OP.")
                else:
                    nfs_da_op = df_nfs_acomp[df_nfs_acomp["op_lavacao_id"] == op_id_sel].copy()

                    if nfs_da_op.empty:
                        st.warning("Nenhuma NF vinculada a esta OP.")
                    else:
                        # Filtrar producao pela OP
                        if not df_prod.empty and "numero_op" in df_prod.columns:
                            prod_da_op = df_prod[df_prod["numero_op"] == numero_op_sel].copy()
                        else:
                            prod_da_op = pd.DataFrame()

                        # Construir tabela de acompanhamento
                        linhas_acomp = []
                        total_qtd_plan = 0
                        total_qtd_real = 0
                        total_peso_plan = 0.0
                        total_peso_real = 0.0

                        for _, nf_row in nfs_da_op.iterrows():
                            nf_numero = str(nf_row["nf_apara"])
                            fornecedor_nf = str(nf_row.get("fornecedor", ""))
                            tipo_nf = str(nf_row.get("tipo_fardo", ""))
                            qtd_plan = int(nf_row.get("quant_fardos", 0) or 0)
                            peso_plan = float(nf_row.get("peso_kg", 0) or 0)

                            # Calcular realizado
                            qtd_real = 0
                            peso_real = 0.0
                            if not prod_da_op.empty and "nf" in prod_da_op.columns:
                                prod_nf = prod_da_op[prod_da_op["nf"].astype(str) == nf_numero]
                                if not prod_nf.empty:
                                    qtd_real = int(pd.to_numeric(prod_nf["quantidade"], errors="coerce").fillna(0).sum())
                                    peso_real = float(pd.to_numeric(prod_nf["peso_kg"], errors="coerce").fillna(0).sum())

                            qtd_rest = qtd_plan - qtd_real
                            peso_rest = peso_plan - peso_real
                            perc_concl = (qtd_real / qtd_plan * 100) if qtd_plan > 0 else 0.0

                            total_qtd_plan += qtd_plan
                            total_qtd_real += qtd_real
                            total_peso_plan += peso_plan
                            total_peso_real += peso_real

                            linhas_acomp.append({
                                "NF": nf_numero,
                                "Fornecedor": fornecedor_nf,
                                "Tipo": tipo_nf,
                                "Qtd Plan.": qtd_plan,
                                "Qtd Real.": qtd_real,
                                "Qtd Rest.": qtd_rest,
                                "Peso Plan.": peso_plan,
                                "Peso Real.": peso_real,
                                "Peso Rest.": peso_rest,
                                "% Concl.": round(perc_concl, 1),
                            })

                        df_acomp = pd.DataFrame(linhas_acomp)

                        # Colorir linhas com base no progresso
                        def cor_progresso(val):
                            if val >= 100:
                                return "background-color: #d4edda; color: #155724"
                            elif val > 0:
                                return "background-color: #fff3cd; color: #856404"
                            else:
                                return "background-color: #f8d7da; color: #721c24"

                        styled = df_acomp.style.applymap(cor_progresso, subset=["% Concl."])
                        st.dataframe(styled, use_container_width=True, hide_index=True)

                        # Progresso geral
                        st.divider()
                        st.subheader("Progresso Geral")

                        total_qtd_rest = total_qtd_plan - total_qtd_real
                        total_peso_rest = total_peso_plan - total_peso_real
                        perc_geral = (total_qtd_real / total_qtd_plan * 100) if total_qtd_plan > 0 else 0.0
                        progresso_barra = min(perc_geral / 100.0, 1.0)

                        col_p1, col_p2, col_p3 = st.columns(3)
                        col_p1.metric("Qtd Planejada", total_qtd_plan)
                        col_p2.metric("Qtd Realizada", total_qtd_real)
                        col_p3.metric("Qtd Restante", total_qtd_rest)

                        col_w1, col_w2, col_w3 = st.columns(3)
                        col_w1.metric("Peso Planejado", formatar_peso(total_peso_plan))
                        col_w2.metric("Peso Realizado", formatar_peso(total_peso_real))
                        col_w3.metric("Peso Restante", formatar_peso(total_peso_rest))

                        st.progress(progresso_barra, text=f"Progresso: {perc_geral:.1f}%")

                        if perc_geral >= 100:
                            st.success("OP 100% concluida! Voce pode fechar esta OP.")
                        elif perc_geral > 0:
                            st.info(f"OP em andamento - {perc_geral:.1f}% concluido.")
                        else:
                            st.warning("Producao ainda nao iniciada para esta OP.")

                        # Botao de fechamento
                        st.divider()
                        st.subheader("Fechar OP")
                        if perc_geral >= 100:
                            st.caption("Toda a producao planejada foi concluida.")
                        else:
                            st.caption(f"Atencao: a OP esta com {perc_geral:.1f}% concluido. Fechar antes de 100% encerrara a OP com producao parcial.")

                        if st.button(f"Fechar OP {numero_op_sel}", type="primary", key="btn_fechar_op"):
                            try:
                                update_rows("op_lavacao", "id", [str(op_id_sel)], "status", "fechada")
                                st.toast("OP fechada com sucesso!")
                                st.success(f"OP **{numero_op_sel}** fechada. Producao final: {formatar_peso(total_peso_real)} ({perc_geral:.1f}%)")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Erro ao fechar OP: {exc}")

# ===========================================================================
# TAB 4: Consultar OPs
# ===========================================================================
with tab_consultar:
    st.subheader("Consultar Ordens de Producao")

    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1:
        data_inicio = st.date_input(
            "Data Inicio",
            value=date.today() - timedelta(days=30),
            key="filtro_data_inicio",
        )
    with col_filtro2:
        data_fim = st.date_input(
            "Data Fim",
            value=date.today(),
            key="filtro_data_fim",
        )

    try:
        df_ops = read_sheet("op_lavacao")
    except Exception as exc:
        st.error(f"Erro ao carregar OPs: {exc}")
        df_ops = pd.DataFrame()

    if df_ops.empty:
        st.info("Nenhuma OP encontrada.")
    else:
        df_ops["data_dt"] = pd.to_datetime(df_ops["data"], errors="coerce").dt.date
        mask = (df_ops["data_dt"] >= data_inicio) & (df_ops["data_dt"] <= data_fim)
        df_filtrado = df_ops[mask].copy()

        if df_filtrado.empty:
            st.info("Nenhuma OP encontrada no periodo selecionado.")
        else:
            df_exibir = df_filtrado[
                ["numero_op", "data", "responsavel", "cliente", "volume_ton",
                 "produto", "indice_fluidez", "status", "observacao"]
            ].copy()
            df_exibir["data"] = df_exibir["data"].apply(formatar_data)

            st.dataframe(df_exibir, use_container_width=True, hide_index=True)

            st.subheader("Detalhes das OPs")
            try:
                df_nfs_all = read_sheet("op_lavacao_nfs")
            except Exception:
                df_nfs_all = pd.DataFrame()

            for _, row in df_filtrado.iterrows():
                with st.expander(f"OP {row['numero_op']} - {formatar_data(row['data'])} - {row['status']}"):
                    col_det1, col_det2, col_det3 = st.columns(3)
                    with col_det1:
                        st.markdown(f"**Responsavel:** {row['responsavel']}")
                        st.markdown(f"**Cliente:** {row['cliente']}")
                    with col_det2:
                        st.markdown(f"**Volume:** {row['volume_ton']} ton")
                        st.markdown(f"**Produto:** {row['produto']}")
                    with col_det3:
                        st.markdown(f"**Indice Fluidez:** {row['indice_fluidez']}")
                        st.markdown(f"**Observacao:** {row.get('observacao', '')}")

                    nfs_lista = []
                    if not df_nfs_all.empty:
                        nfs_desta_op = df_nfs_all[df_nfs_all["op_lavacao_id"] == row["id"]]
                        if not nfs_desta_op.empty:
                            st.caption("Notas Fiscais vinculadas:")
                            cols_nf = ["nf_apara", "fornecedor", "tipo_fardo", "quant_fardos", "peso_kg", "obs"]
                            cols_presentes = [c for c in cols_nf if c in nfs_desta_op.columns]
                            st.dataframe(
                                nfs_desta_op[cols_presentes],
                                use_container_width=True,
                                hide_index=True,
                            )
                            nfs_lista = nfs_desta_op.to_dict("records")
                        else:
                            st.caption("Nenhuma NF vinculada a esta OP.")
                    else:
                        st.caption("Nenhuma NF vinculada a esta OP.")

                    if gerar_pdf_op_lavacao is not None:
                        try:
                            op_dict = row.to_dict()
                            pdf_bytes = gerar_pdf_op_lavacao(op_dict, nfs_lista)
                            st.download_button(
                                "Baixar PDF da OP",
                                pdf_bytes,
                                file_name=f"{row['numero_op']}.pdf",
                                mime="application/pdf",
                                key=f"pdf_op_lav_{row['numero_op']}",
                            )
                        except Exception:
                            pass
