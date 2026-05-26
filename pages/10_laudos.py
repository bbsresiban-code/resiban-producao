import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd

from utils.database import read_sheet, read_sheet_no_cache
from utils.formatters import formatar_data, formatar_peso

try:
    from utils.pdf_generator import gerar_pdf_laudo_tecnico
except ImportError:
    gerar_pdf_laudo_tecnico = None

# ---------------------------------------------------------------------------
# Titulo
# ---------------------------------------------------------------------------
st.header("Laudos Tecnicos")

tab_gerar, tab_historico = st.tabs(["Gerar Laudo", "Historico"])

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
