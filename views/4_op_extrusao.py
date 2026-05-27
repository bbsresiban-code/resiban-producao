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

    with st.form("form_nova_op_extrusao", clear_on_submit=True):
        col1, col2 = st.columns(2)

        with col1:
            numero_op = proximo_sequencial("op_extrusao", "numero_op", "OPE")
            st.info(f"Numero da OP: **{numero_op}**")
            data_op = st.date_input("Data", value=date.today())
            responsavel = st.text_input("Responsavel")
            cliente = st.text_input("Cliente")
            volume_ton = st.number_input(
                "Volume (ton)", min_value=0.0, step=0.5, format="%.1f"
            )

        with col2:
            origem = st.selectbox("Origem do Material", ["Proprio", "Servico"])
            produto = st.text_input("Produto")
            maquina = st.selectbox("Maquina", options=EXTRUSORAS, format_func=lambda x: f"Extrusora {x}")
            coordenador = st.text_input("Coordenador")
            observacao = st.text_area("Observacao")

        submitted = st.form_submit_button("Criar OP", use_container_width=True)

        if submitted:
            erros = []
            if not responsavel.strip():
                erros.append("Responsavel e obrigatorio.")

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
                        "volume_ton": volume_ton,
                        "origem": origem,
                        "tipo_lote": tipo_lote,
                        "produto": produto.strip(),
                        "maquina": maquina,
                        "data_inicio": "",
                        "data_final": "",
                        "coordenador": coordenador.strip(),
                        "producao_final_kg": "",
                        "perda_percentual": "",
                        "status": "aberta",
                        "observacao": observacao.strip(),
                    }
                    append_row("op_extrusao", dados)
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
                    value=float(total_kg),
                    step=0.5,
                    format="%.1f",
                )
                perda_percentual = st.number_input(
                    "Perda (%)",
                    min_value=0.0,
                    max_value=100.0,
                    step=0.1,
                    format="%.2f",
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
                                        producao_final_kg,
                                    )
                                if "perda_percentual" in headers:
                                    ws.update_cell(
                                        idx,
                                        headers.index("perda_percentual") + 1,
                                        perda_percentual,
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
                            f"Producao: {formatar_peso(producao_final_kg)} | "
                            f"Perda: {formatar_percentual(perda_percentual)}"
                        )
                    except Exception as exc:
                        st.error(f"Erro ao fechar OP: {exc}")
    else:
        st.info("Nenhuma OP cadastrada ou todas ja estao fechadas.")
