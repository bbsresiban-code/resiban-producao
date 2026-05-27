import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd

from utils.database import read_sheet, read_sheet_no_cache
from utils.formatters import formatar_data, formatar_peso

try:
    from utils.pdf_generator import gerar_pdf_laudo_tecnico, gerar_pdf_laudo_rastreabilidade
except ImportError:
    gerar_pdf_laudo_tecnico = None
    gerar_pdf_laudo_rastreabilidade = None

# ---------------------------------------------------------------------------
# Titulo
# ---------------------------------------------------------------------------
st.header("Laudos")

tab_gerar, tab_rastreio, tab_historico = st.tabs(["Laudo Tecnico", "Laudo de Rastreabilidade", "Historico"])

# ===========================================================================
# TAB: Gerar Laudo
# ===========================================================================
with tab_gerar:
    st.subheader("Gerar Laudo Tecnico")

    # Carregar romaneios
    try:
        df_rom = read_sheet_no_cache("romaneio")
    except Exception as exc:
        st.error(f"Erro ao carregar romaneios: {exc}")
        df_rom = pd.DataFrame()

    if df_rom.empty:
        st.info("Nenhum romaneio encontrado.")
    else:
        # Preparar opcoes do selectbox
        opcoes_rom = {}
        for _, row in df_rom.iterrows():
            numero = row.get("numero_pedido", "")
            cliente = row.get("cliente", "")
            data = formatar_data(row.get("data", ""))
            label = f"{numero} - Cliente: {cliente} - Data: {data}"
            opcoes_rom[label] = row.to_dict()

        romaneio_selecionado_label = st.selectbox(
            "Selecione o Romaneio",
            options=list(opcoes_rom.keys()),
            key="laudo_rom_select",
        )

        if romaneio_selecionado_label:
            romaneio_info = opcoes_rom[romaneio_selecionado_label]
            romaneio_id = romaneio_info.get("id", "")

            st.markdown(f"**Romaneio:** {romaneio_info.get('numero_pedido', '')}")
            st.markdown(f"**Cliente:** {romaneio_info.get('cliente', '')}")
            st.markdown(f"**Data:** {formatar_data(romaneio_info.get('data', ''))}")

            # Carregar itens do romaneio
            try:
                df_itens = read_sheet_no_cache("romaneio_itens")
            except Exception as exc:
                st.error(f"Erro ao carregar itens do romaneio: {exc}")
                df_itens = pd.DataFrame()

            # Carregar dados de qualidade
            try:
                df_qual = read_sheet("qualidade")
            except Exception as exc:
                st.error(f"Erro ao carregar dados de qualidade: {exc}")
                df_qual = pd.DataFrame()

            if df_itens.empty:
                st.warning("Nenhum item encontrado para romaneios.")
            else:
                itens_rom = df_itens[df_itens["romaneio_id"] == romaneio_id].copy()

                if itens_rom.empty:
                    st.warning("Nenhum item encontrado para este romaneio.")
                else:
                    # Cruzar com qualidade
                    itens_qualidade = []
                    for _, item in itens_rom.iterrows():
                        codigo_lote = item.get("codigo_lote", "")
                        peso_kg = item.get("peso_kg", 0)

                        qual_data = {
                            "codigo_lote": codigo_lote,
                            "grade": "",
                            "cor": "",
                            "mfi": "",
                            "teor_cinzas": "",
                            "densidade": "",
                            "umidade": "",
                            "teste_filme": "",
                            "peso_kg": peso_kg,
                        }

                        if not df_qual.empty and "codigo_lote" in df_qual.columns:
                            match = df_qual[df_qual["codigo_lote"] == codigo_lote]
                            if not match.empty:
                                ultimo = match.iloc[-1]
                                qual_data["grade"] = ultimo.get("grade", "")
                                qual_data["cor"] = ultimo.get("cor", "")
                                qual_data["mfi"] = ultimo.get("mfi", "")
                                qual_data["teor_cinzas"] = ultimo.get("teor_cinzas", "")
                                qual_data["densidade"] = ultimo.get("densidade", "")
                                qual_data["umidade"] = ultimo.get("umidade", "")
                                qual_data["teste_filme"] = ultimo.get("teste_filme", "")

                        itens_qualidade.append(qual_data)

                    # Montar tabela para exibicao
                    df_exibir = pd.DataFrame(itens_qualidade)
                    df_exibir_tabela = df_exibir[
                        [
                            "codigo_lote",
                            "grade",
                            "cor",
                            "mfi",
                            "teor_cinzas",
                            "densidade",
                            "umidade",
                            "teste_filme",
                        ]
                    ].copy()
                    df_exibir_tabela.columns = [
                        "Lote",
                        "Grade",
                        "Cor",
                        "MFI",
                        "Cinzas",
                        "Densidade",
                        "Umidade",
                        "Filme",
                    ]

                    st.markdown("#### Dados de Qualidade dos Lotes")
                    st.dataframe(
                        df_exibir_tabela,
                        use_container_width=True,
                        hide_index=True,
                    )

                    st.caption(f"Total de lotes: {len(itens_qualidade)}")

                    # Botao para gerar PDF
                    st.divider()

                    if gerar_pdf_laudo_tecnico is None:
                        st.warning(
                            "O modulo de geracao de PDF ainda nao esta disponivel. "
                            "O botao de download sera habilitado quando o modulo "
                            "utils.pdf_generator for implementado."
                        )
                    else:
                        try:
                            pdf_bytes = gerar_pdf_laudo_tecnico(
                                romaneio=romaneio_info,
                                itens_qualidade=itens_qualidade,
                            )
                            nome_arquivo = (
                                f"laudo_tecnico_{romaneio_info.get('numero_pedido', 'ROM')}.pdf"
                            )
                            st.download_button(
                                label="Baixar Laudo Tecnico (PDF)",
                                data=pdf_bytes,
                                file_name=nome_arquivo,
                                mime="application/pdf",
                                type="primary",
                                use_container_width=True,
                            )
                        except Exception as exc:
                            st.error(f"Erro ao gerar PDF do laudo: {exc}")


# ===========================================================================
# TAB: Laudo de Rastreabilidade
# ===========================================================================
with tab_rastreio:
    st.subheader("Laudo de Rastreabilidade")

    try:
        df_rom_rast = read_sheet_no_cache("romaneio")
    except Exception:
        df_rom_rast = pd.DataFrame()

    if df_rom_rast.empty:
        st.info("Nenhum romaneio encontrado.")
    else:
        opcoes_rast = {}
        for _, row in df_rom_rast.iterrows():
            numero = row.get("numero_pedido", "")
            cliente = row.get("cliente", "")
            data = formatar_data(row.get("data", ""))
            label = f"{numero} - Cliente: {cliente} - Data: {data}"
            opcoes_rast[label] = row.to_dict()

        rast_label = st.selectbox("Selecione o Romaneio", options=list(opcoes_rast.keys()), key="rast_rom_select")

        if rast_label:
            rast_info = opcoes_rast[rast_label]
            rast_id = rast_info.get("id", "")

            st.markdown(f"**Romaneio:** {rast_info.get('numero_pedido', '')} | **Cliente:** {rast_info.get('cliente', '')} | **Data:** {formatar_data(rast_info.get('data', ''))}")

            try:
                df_itens_rast = read_sheet_no_cache("romaneio_itens")
                df_ext_rast = read_sheet("producao_extrusao")
                df_ops_ext_rast = read_sheet("op_extrusao")
                df_ops_lav_rast = read_sheet("op_lavacao")
                df_nfs_rast = read_sheet("op_lavacao_nfs")
                df_qual_rast = read_sheet("qualidade")
            except Exception:
                df_itens_rast = pd.DataFrame()
                df_ext_rast = pd.DataFrame()
                df_ops_ext_rast = pd.DataFrame()
                df_ops_lav_rast = pd.DataFrame()
                df_nfs_rast = pd.DataFrame()
                df_qual_rast = pd.DataFrame()

            if df_itens_rast.empty:
                st.warning("Nenhum item encontrado.")
            else:
                itens_rom_rast = df_itens_rast[df_itens_rast["romaneio_id"] == rast_id]

                if itens_rom_rast.empty:
                    st.warning("Nenhum item neste romaneio.")
                else:
                    itens_rastreio = []
                    for _, item in itens_rom_rast.iterrows():
                        codigo_lote = str(item.get("codigo_lote", ""))
                        peso_kg = item.get("peso_kg", 0)

                        ope = ""
                        opl = ""
                        origem = ""
                        nfs_mp = []
                        grade = ""
                        cor = ""

                        if not df_ext_rast.empty and "codigo_lote" in df_ext_rast.columns:
                            lote_row = df_ext_rast[df_ext_rast["codigo_lote"].astype(str) == codigo_lote]
                            if not lote_row.empty:
                                lote_data = lote_row.iloc[0]
                                ope = str(lote_data.get("numero_op", ""))
                                opl = str(lote_data.get("opl_origem", ""))

                                if ope and not df_ops_ext_rast.empty:
                                    ope_row = df_ops_ext_rast[df_ops_ext_rast["numero_op"].astype(str) == ope]
                                    if not ope_row.empty:
                                        origem = str(ope_row.iloc[0].get("origem", ""))

                                if opl and not df_ops_lav_rast.empty and not df_nfs_rast.empty:
                                    opl_row = df_ops_lav_rast[df_ops_lav_rast["numero_op"].astype(str) == opl]
                                    if not opl_row.empty:
                                        opl_id = str(opl_row.iloc[0]["id"])
                                        nfs_da_opl = df_nfs_rast[df_nfs_rast["op_lavacao_id"].astype(str) == opl_id]
                                        if not nfs_da_opl.empty:
                                            nfs_mp = nfs_da_opl["nf_apara"].astype(str).tolist()

                        if not df_qual_rast.empty and "codigo_lote" in df_qual_rast.columns:
                            qual_match = df_qual_rast[df_qual_rast["codigo_lote"].astype(str) == codigo_lote]
                            if not qual_match.empty:
                                grade = str(qual_match.iloc[-1].get("grade", ""))
                                cor = str(qual_match.iloc[-1].get("cor", ""))

                        itens_rastreio.append({
                            "codigo_lote": codigo_lote,
                            "peso_kg": peso_kg,
                            "ope": ope,
                            "origem": origem,
                            "opl": opl,
                            "nfs_mp": nfs_mp,
                            "grade": grade,
                            "cor": cor,
                        })

                    df_rast_exibir = pd.DataFrame([
                        {
                            "Lote": i["codigo_lote"],
                            "Peso (kg)": i["peso_kg"],
                            "OPE": i["ope"],
                            "Origem": i["origem"],
                            "OPL": i["opl"],
                            "NFs MP": ", ".join(i["nfs_mp"]) if isinstance(i["nfs_mp"], list) else i["nfs_mp"],
                            "Grade": i["grade"],
                            "Cor": i["cor"],
                        }
                        for i in itens_rastreio
                    ])

                    st.markdown("#### Rastreabilidade dos Lotes")
                    st.dataframe(df_rast_exibir, use_container_width=True, hide_index=True)

                    st.divider()
                    if gerar_pdf_laudo_rastreabilidade is None:
                        st.warning("Modulo PDF nao disponivel.")
                    else:
                        try:
                            pdf_rast = gerar_pdf_laudo_rastreabilidade(rast_info, itens_rastreio)
                            st.download_button(
                                "Baixar Laudo de Rastreabilidade (PDF)",
                                pdf_rast,
                                file_name=f"rastreabilidade_{rast_info.get('numero_pedido', 'ROM')}.pdf",
                                mime="application/pdf",
                                type="primary",
                                use_container_width=True,
                            )
                        except Exception as exc:
                            st.error(f"Erro ao gerar PDF: {exc}")


# ===========================================================================
# TAB: Historico
# ===========================================================================
with tab_historico:
    st.subheader("Historico de Romaneios")

    try:
        df_rom_hist = read_sheet("romaneio")
    except Exception as exc:
        st.error(f"Erro ao carregar romaneios: {exc}")
        df_rom_hist = pd.DataFrame()

    if df_rom_hist.empty:
        st.info("Nenhum romaneio encontrado.")
    else:
        df_rom_hist = df_rom_hist.sort_values(
            by="data",
            ascending=False,
            key=lambda col: pd.to_datetime(col, errors="coerce"),
        )

        for idx, row in df_rom_hist.iterrows():
            numero = row.get("numero_pedido", "")
            cliente = row.get("cliente", "")
            data = formatar_data(row.get("data", ""))
            peso = row.get("peso_total_kg", 0)
            try:
                peso = float(peso)
            except (ValueError, TypeError):
                peso = 0.0

            label = (
                f"{numero} | Cliente: {cliente} | "
                f"Data: {data} | {formatar_peso(peso)}"
            )

            with st.expander(label):
                st.markdown(f"**Romaneio:** {numero}")
                st.markdown(f"**Cliente:** {cliente}")
                st.markdown(f"**Data:** {data}")
                st.markdown(f"**Peso Total:** {formatar_peso(peso)}")

                if gerar_pdf_laudo_tecnico is None:
                    st.caption(
                        "Geracao de PDF indisponivel (modulo pdf_generator nao encontrado)."
                    )
                else:
                    romaneio_dict = row.to_dict()
                    romaneio_id_hist = row.get("id", "")

                    # Carregar itens e qualidade para regenerar
                    try:
                        df_itens_hist = read_sheet("romaneio_itens")
                        df_qual_hist = read_sheet("qualidade")
                    except Exception as exc:
                        st.error(f"Erro ao carregar dados: {exc}")
                        df_itens_hist = pd.DataFrame()
                        df_qual_hist = pd.DataFrame()

                    if not df_itens_hist.empty:
                        itens_hist = df_itens_hist[
                            df_itens_hist["romaneio_id"] == romaneio_id_hist
                        ]

                        if not itens_hist.empty:
                            itens_qual_hist = []
                            for _, item in itens_hist.iterrows():
                                codigo_lote = item.get("codigo_lote", "")
                                peso_kg = item.get("peso_kg", 0)

                                qual_item = {
                                    "codigo_lote": codigo_lote,
                                    "grade": "",
                                    "cor": "",
                                    "mfi": "",
                                    "teor_cinzas": "",
                                    "densidade": "",
                                    "umidade": "",
                                    "teste_filme": "",
                                    "peso_kg": peso_kg,
                                }

                                if (
                                    not df_qual_hist.empty
                                    and "codigo_lote" in df_qual_hist.columns
                                ):
                                    match = df_qual_hist[
                                        df_qual_hist["codigo_lote"] == codigo_lote
                                    ]
                                    if not match.empty:
                                        ultimo = match.iloc[-1]
                                        qual_item["grade"] = ultimo.get("grade", "")
                                        qual_item["cor"] = ultimo.get("cor", "")
                                        qual_item["mfi"] = ultimo.get("mfi", "")
                                        qual_item["teor_cinzas"] = ultimo.get(
                                            "teor_cinzas", ""
                                        )
                                        qual_item["densidade"] = ultimo.get(
                                            "densidade", ""
                                        )
                                        qual_item["umidade"] = ultimo.get(
                                            "umidade", ""
                                        )
                                        qual_item["teste_filme"] = ultimo.get(
                                            "teste_filme", ""
                                        )

                                itens_qual_hist.append(qual_item)

                            try:
                                pdf_bytes_hist = gerar_pdf_laudo_tecnico(
                                    romaneio=romaneio_dict,
                                    itens_qualidade=itens_qual_hist,
                                )
                                nome_arquivo_hist = (
                                    f"laudo_tecnico_{numero}.pdf"
                                )
                                st.download_button(
                                    label="Regenerar Laudo Tecnico (PDF)",
                                    data=pdf_bytes_hist,
                                    file_name=nome_arquivo_hist,
                                    mime="application/pdf",
                                    key=f"download_hist_{romaneio_id_hist}",
                                )
                            except Exception as exc:
                                st.error(f"Erro ao gerar PDF: {exc}")
                        else:
                            st.caption("Nenhum item encontrado para este romaneio.")
                    else:
                        st.caption("Nenhum item de romaneio encontrado.")
