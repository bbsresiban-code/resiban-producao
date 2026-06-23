import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, datetime

from utils.database import read_sheet, append_row, update_rows, update_row_multi, read_sheet_no_cache, proximo_sequencial
from utils.formatters import EXTRUSORAS, formatar_peso, formatar_data, formatar_percentual

try:
    from utils.pdf_generator import gerar_pdf_op_extrusao
except ImportError:
    gerar_pdf_op_extrusao = None

st.title("OP Extrusao")

usuario_logado = st.session_state.get("usuario", "master")
perfil_logado = st.session_state.get("perfil", "master")

tab_nova, tab_editar, tab_consultar, tab_fechar = st.tabs(["Nova OP", "Editar OP", "Consultar OPs", "Fechar OP"])

# ------------------------------------------------------------------------------
# Tab: Nova OP
# ------------------------------------------------------------------------------
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
                # OPLs ja empenhadas em alguma OPE nao podem ser reutilizadas
                opls_empenhadas = set()
                try:
                    df_ope_exist = read_sheet_no_cache("op_extrusao")
                    if not df_ope_exist.empty and "opl_origem" in df_ope_exist.columns:
                        opls_empenhadas = set(
                            df_ope_exist["opl_origem"].dropna().astype(str).str.strip()
                        ) - {""}
                except Exception:
                    opls_empenhadas = set()

                opls_disponiveis = [
                    o for o in df_opl["numero_op"].astype(str).tolist()
                    if o not in opls_empenhadas
                ]

                if not opls_disponiveis:
                    st.warning(
                        "Nenhuma OPL livre. Todas as OPLs ja foram empenhadas em OPEs "
                        "anteriores."
                    )
                    opl_vinculada = ""
                else:
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
            "Aditivo (%)", min_value=0.0, max_value=100.0, step=0.01, value=None, format="%.2f",
            key="ope_aditivo_pct",
            help="Percentual de aditivo no material (aceita ate 2 casas decimais)",
        )

    aditivo_kg_total = volume_ton * 1000 * ((aditivo_percentual or 0) / 100)
    perc_reciclado_op = 100 - (aditivo_percentual or 0)
    if (aditivo_percentual or 0) > 0 and volume_ton > 0:
        st.info(
            f"Aditivo total: **{aditivo_kg_total:,.2f} kg** "
            f"({(aditivo_percentual or 0):.2f}% de {volume_ton:.2f} ton)  \n"
            f"Conteudo reciclado: **{perc_reciclado_op:.2f}%**"
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

# ------------------------------------------------------------------------------
# Tab: Editar OP
# ------------------------------------------------------------------------------
with tab_editar:
    st.subheader("Editar Ordem de Producao - Extrusao (em aberto)")

    try:
        df_ops_edit = read_sheet_no_cache("op_extrusao")
    except Exception:
        df_ops_edit = pd.DataFrame()

    if df_ops_edit.empty or "status" not in df_ops_edit.columns:
        st.info("Nenhuma OP cadastrada.")
    else:
        ops_abertas_edit = df_ops_edit[df_ops_edit["status"].astype(str).str.lower() == "aberta"]
        if ops_abertas_edit.empty:
            st.info("Nenhuma OP aberta para editar.")
        else:
            opcoes_edit = ops_abertas_edit.apply(
                lambda r: f"{r['numero_op']} - {r.get('cliente', '')} ({formatar_data(r['data'])})",
                axis=1,
            ).tolist()
            op_edit_label = st.selectbox("Selecione a OP", opcoes_edit, key="ope_edit_sel")

            if op_edit_label:
                idx_edit = opcoes_edit.index(op_edit_label)
                op_edit = ops_abertas_edit.iloc[idx_edit]
                op_edit_num = str(op_edit["numero_op"])
                volume_atual = float(op_edit.get("volume_ton", 0) or 0)

                st.markdown(
                    f"**OP:** {op_edit_num} | **Origem:** {op_edit.get('origem', '-')} | "
                    f"**Volume:** {volume_atual:.2f} ton"
                )
                if str(op_edit.get("origem", "")).strip().lower() == "servico":
                    st.caption(
                        "O volume vem das aparas de servico. Para troca-las, use a "
                        "secao 'Aparas de Servico vinculadas' abaixo."
                    )
                else:
                    st.caption(
                        "O volume vem da OPL de origem (Proprio) e nao e alterado aqui."
                    )

                st.divider()

                maquina_atual = op_edit.get("maquina", EXTRUSORAS[0] if len(EXTRUSORAS) else "")
                try:
                    idx_maq = list(EXTRUSORAS).index(maquina_atual)
                except ValueError:
                    idx_maq = 0

                try:
                    data_atual = pd.to_datetime(op_edit.get("data")).date()
                except Exception:
                    data_atual = date.today()

                with st.form("form_editar_ope", clear_on_submit=False):
                    col_e1, col_e2 = st.columns(2)
                    with col_e1:
                        edit_data = st.date_input("Data", value=data_atual, key="ope_edit_data")
                        edit_resp = st.text_input(
                            "Responsavel",
                            value=str(op_edit.get("responsavel", "") or ""),
                            key="ope_edit_resp",
                        )
                        edit_cliente = st.text_input(
                            "Cliente",
                            value=str(op_edit.get("cliente", "") or ""),
                            key="ope_edit_cliente",
                        )
                    with col_e2:
                        edit_produto = st.text_input(
                            "Produto",
                            value=str(op_edit.get("produto", "") or ""),
                            key="ope_edit_prod",
                        )
                        edit_maquina = st.selectbox(
                            "Maquina",
                            options=EXTRUSORAS,
                            index=idx_maq,
                            format_func=lambda x: f"Extrusora {x}",
                            key="ope_edit_maq",
                        )
                        edit_aditivo = st.number_input(
                            "Aditivo (%)",
                            min_value=0.0,
                            max_value=100.0,
                            step=0.01,
                            format="%.2f",
                            value=float(op_edit.get("aditivo_percentual", 0) or 0),
                            key="ope_edit_aditivo",
                            help="Percentual de aditivo no material (aceita ate 2 casas decimais)",
                        )

                    edit_obs = st.text_area(
                        "Observacao",
                        value=str(op_edit.get("observacao", "") or ""),
                        key="ope_edit_obs",
                    )

                    edit_aditivo_kg = volume_atual * 1000 * ((edit_aditivo or 0) / 100)
                    edit_perc_reciclado = 100 - (edit_aditivo or 0)
                    st.caption(
                        f"Aditivo total recalculado: {edit_aditivo_kg:,.2f} kg | "
                        f"Conteudo reciclado: {edit_perc_reciclado:.2f}%"
                    )

                    edit_submit = st.form_submit_button(
                        "Salvar Alteracoes", type="primary", use_container_width=True
                    )

                if edit_submit:
                    if not edit_resp.strip():
                        st.error("Responsavel e obrigatorio.")
                    else:
                        try:
                            updates = {
                                "data": edit_data.isoformat(),
                                "responsavel": edit_resp.strip(),
                                "cliente": edit_cliente.strip(),
                                "produto": edit_produto.strip(),
                                "maquina": edit_maquina,
                                "aditivo_percentual": float(edit_aditivo or 0),
                                "aditivo_kg_total": float(edit_aditivo_kg),
                                "observacao": edit_obs.strip(),
                            }
                            update_row_multi("op_extrusao", "numero_op", op_edit_num, updates)
                            st.toast("OP atualizada com sucesso!")
                            st.success(f"OP **{op_edit_num}** atualizada com sucesso.")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erro ao atualizar OP: {exc}")

                # ----------------------------------------------------------
                # Edicao de aparas (somente OPE de Servico aberta)
                # ----------------------------------------------------------
                if str(op_edit.get("origem", "")).strip().lower() == "servico":
                    st.divider()
                    st.markdown("#### Aparas de Servico vinculadas")
                    st.caption(
                        "Adicione ou remova aparas desta OPE de servico. O volume "
                        "e o aditivo total sao recalculados automaticamente."
                    )

                    try:
                        df_aparas_all = read_sheet_no_cache("aparas_estoque")
                    except Exception:
                        df_aparas_all = pd.DataFrame()

                    cols_ok = (
                        not df_aparas_all.empty
                        and "tipo_material" in df_aparas_all.columns
                        and "opl_em_uso" in df_aparas_all.columns
                        and "status" in df_aparas_all.columns
                    )

                    if not cols_ok:
                        st.info("Nenhuma apara cadastrada (ou colunas ausentes).")
                    else:
                        df_aparas_all["peso_kg"] = pd.to_numeric(
                            df_aparas_all["peso_kg"], errors="coerce"
                        ).fillna(0)

                        vinc = df_aparas_all[
                            (df_aparas_all["tipo_material"].astype(str) == "Servico")
                            & (df_aparas_all["opl_em_uso"].astype(str) == op_edit_num)
                        ].copy()
                        disp = df_aparas_all[
                            (df_aparas_all["tipo_material"].astype(str) == "Servico")
                            & (df_aparas_all["status"].astype(str) == "disponivel")
                        ].copy()

                        cols_apara = [
                            "numero_nf", "fornecedor", "qualidade",
                            "tipo_fardo", "quantidade", "peso_kg",
                        ]
                        col_cfg_base = {
                            "numero_nf": "NF", "fornecedor": "Fornecedor",
                            "qualidade": "Qual.", "tipo_fardo": "Tipo",
                            "quantidade": "Qtd", "peso_kg": "Peso (kg)",
                        }

                        st.markdown("**Vinculadas atualmente** (marque para remover)")
                        remover_ids = []
                        if vinc.empty:
                            st.caption("Nenhuma apara vinculada a esta OPE.")
                        else:
                            vinc_view = vinc[cols_apara].copy()
                            vinc_view.insert(0, "remover", False)
                            edited_vinc = st.data_editor(
                                vinc_view, use_container_width=True, hide_index=True,
                                disabled=cols_apara,
                                column_config={
                                    "remover": st.column_config.CheckboxColumn("Remover"),
                                    **col_cfg_base,
                                },
                                key=f"ope_edit_vinc_{op_edit_num}",
                            )
                            for _, r in edited_vinc[edited_vinc["remover"] == True].iterrows():
                                orig = vinc[vinc["numero_nf"].astype(str) == str(r["numero_nf"])].iloc[0]
                                remover_ids.append(str(orig["id"]))

                        st.markdown("**Disponiveis para adicionar** (marque para adicionar)")
                        adicionar_ids = []
                        if disp.empty:
                            st.caption("Nenhuma apara de servico disponivel para adicionar.")
                        else:
                            disp_view = disp[cols_apara].copy()
                            disp_view.insert(0, "adicionar", False)
                            edited_disp = st.data_editor(
                                disp_view, use_container_width=True, hide_index=True,
                                disabled=cols_apara,
                                column_config={
                                    "adicionar": st.column_config.CheckboxColumn("Adicionar"),
                                    **col_cfg_base,
                                },
                                key=f"ope_edit_disp_{op_edit_num}",
                            )
                            for _, r in edited_disp[edited_disp["adicionar"] == True].iterrows():
                                orig = disp[disp["numero_nf"].astype(str) == str(r["numero_nf"])].iloc[0]
                                adicionar_ids.append(str(orig["id"]))

                        ids_atuais = set(vinc["id"].astype(str)) if not vinc.empty else set()
                        ids_finais = (ids_atuais - set(remover_ids)) | set(adicionar_ids)
                        peso_final = float(
                            df_aparas_all[df_aparas_all["id"].astype(str).isin(ids_finais)]["peso_kg"].sum()
                        )
                        novo_volume = peso_final / 1000
                        aditivo_pct_atual = float(op_edit.get("aditivo_percentual", 0) or 0)
                        novo_aditivo_kg = novo_volume * 1000 * (aditivo_pct_atual / 100)

                        st.info(
                            f"Volume atual: **{volume_atual:.2f} ton** -> "
                            f"novo volume: **{novo_volume:.2f} ton** ({peso_final:,.1f} kg)  \n"
                            f"Aditivo total recalculado: **{novo_aditivo_kg:,.2f} kg** "
                            f"(mantendo {aditivo_pct_atual:.2f}%)"
                        )

                        if st.button(
                            "Salvar aparas da OPE", type="primary",
                            use_container_width=True,
                            key=f"ope_edit_salvar_aparas_{op_edit_num}",
                        ):
                            if not ids_finais:
                                st.error("A OPE de servico precisa ter ao menos uma apara vinculada.")
                            elif not remover_ids and not adicionar_ids:
                                st.warning("Nenhuma alteracao de aparas selecionada.")
                            else:
                                try:
                                    if remover_ids:
                                        update_rows("aparas_estoque", "id", remover_ids, "status", "disponivel")
                                        update_rows("aparas_estoque", "id", remover_ids, "opl_em_uso", "")
                                    if adicionar_ids:
                                        update_rows("aparas_estoque", "id", adicionar_ids, "status", "em_uso")
                                        update_rows("aparas_estoque", "id", adicionar_ids, "opl_em_uso", op_edit_num)
                                    update_row_multi(
                                        "op_extrusao", "numero_op", op_edit_num,
                                        {
                                            "volume_ton": float(novo_volume),
                                            "aditivo_kg_total": float(novo_aditivo_kg),
                                        },
                                    )
                                    st.toast("Aparas da OPE atualizadas!")
                                    st.success(
                                        f"Aparas da OPE **{op_edit_num}** atualizadas. "
                                        f"Novo volume: {novo_volume:.2f} ton."
                                    )
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Erro ao atualizar aparas: {exc}")

                # ----------------------------------------------------------
                # Material extra (somente master) - sem origem em OPL/NF
                # ----------------------------------------------------------
                if perfil_logado == "master":
                    st.divider()
                    st.markdown("#### Material Extra (sem OPL/NF)")
                    st.caption(
                        "Registre material adicionado a OPE sem origem em OPL/NF. O peso "
                        "soma ao volume previsto da OPE e aparece na rastreabilidade."
                    )
                    try:
                        df_extra_all = read_sheet_no_cache("ope_material_extra")
                    except Exception:
                        df_extra_all = pd.DataFrame()
                    if not df_extra_all.empty and "numero_op" in df_extra_all.columns:
                        extras_ope = df_extra_all[
                            df_extra_all["numero_op"].astype(str) == op_edit_num
                        ].copy()
                    else:
                        extras_ope = pd.DataFrame()
                    if not extras_ope.empty:
                        extras_ope["peso_kg"] = pd.to_numeric(
                            extras_ope["peso_kg"], errors="coerce"
                        ).fillna(0)
                        cols_x = [
                            c for c in ["tipo_justificativa", "descricao", "peso_kg",
                                        "registrado_por", "observacao"]
                            if c in extras_ope.columns
                        ]
                        st.dataframe(extras_ope[cols_x], use_container_width=True, hide_index=True)
                        st.caption(
                            f"Total material extra: {formatar_peso(float(extras_ope['peso_kg'].sum()))}"
                        )

                    with st.form(f"form_material_extra_{op_edit_num}", clear_on_submit=True):
                        col_x1, col_x2 = st.columns(2)
                        with col_x1:
                            extra_tipo = st.selectbox(
                                "Justificativa", ["Limpo", "Repasse", "Sem NF"],
                                key=f"extra_tipo_{op_edit_num}",
                            )
                            extra_peso = st.number_input(
                                "Peso (kg)", min_value=0.0, step=0.5, format="%.1f",
                                value=None, key=f"extra_peso_{op_edit_num}",
                            )
                        with col_x2:
                            extra_desc = st.text_input(
                                "Descricao do material", key=f"extra_desc_{op_edit_num}"
                            )
                            extra_obs = st.text_input(
                                "Observacao", key=f"extra_obs_{op_edit_num}"
                            )
                        if st.form_submit_button(
                            "Adicionar material extra", type="primary", use_container_width=True
                        ):
                            if not extra_desc.strip():
                                st.error("Informe a descricao do material.")
                            elif not extra_peso or extra_peso <= 0:
                                st.error("Peso deve ser maior que zero.")
                            else:
                                try:
                                    append_row("ope_material_extra", {
                                        "numero_op": op_edit_num,
                                        "descricao": extra_desc.strip(),
                                        "tipo_justificativa": extra_tipo,
                                        "peso_kg": float(extra_peso or 0),
                                        "registrado_por": usuario_logado,
                                        "observacao": extra_obs.strip(),
                                    })
                                    st.toast("Material extra adicionado!")
                                    st.success(
                                        f"Material extra de {formatar_peso(float(extra_peso or 0))} "
                                        f"adicionado a OPE {op_edit_num}."
                                    )
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Erro ao adicionar material extra: {exc}")

# ------------------------------------------------------------------------------
# Tab: Consultar OPs
# ------------------------------------------------------------------------------
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

# ------------------------------------------------------------------------------
# Tab: Fechar OP
# ------------------------------------------------------------------------------
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
                        update_row_multi(
                            "op_extrusao",
                            "numero_op",
                            op_sel,
                            {
                                "status": "fechada",
                                "producao_final_kg": float(producao_final_kg or 0),
                                "perda_percentual": float(perda_percentual or 0),
                                "data_final": date.today().isoformat(),
                            },
                        )
                        st.success(
                            f"OP {op_sel} fechada com sucesso! "
                            f"Producao: {formatar_peso(float(producao_final_kg or 0))} | "
                            f"Perda: {formatar_percentual(float(perda_percentual or 0))}"
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro ao fechar OP: {exc}")
    else:
        st.info("Nenhuma OP cadastrada ou todas ja estao fechadas.")
