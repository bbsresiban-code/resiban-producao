import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date

from utils.database import read_sheet
from utils.formatters import formatar_peso, formatar_data

st.header("Controle de Servico (Industrializacao para Terceiros)")
st.caption("Materiais de Servico NAO entram no inventario proprio. Sao controlados aqui separadamente.")

try:
    df_aparas = read_sheet("aparas_estoque")
except Exception:
    df_aparas = pd.DataFrame()

try:
    df_ext = read_sheet("producao_extrusao")
except Exception:
    df_ext = pd.DataFrame()

try:
    df_op_ext = read_sheet("op_extrusao")
except Exception:
    df_op_ext = pd.DataFrame()

# ===========================================================================
# Filtrar so SERVICO
# ===========================================================================
if not df_aparas.empty and "tipo_material" in df_aparas.columns:
    df_aparas_serv = df_aparas[df_aparas["tipo_material"].astype(str) == "Servico"].copy()
else:
    df_aparas_serv = pd.DataFrame()

if not df_ext.empty and "tipo" in df_ext.columns:
    df_grao_serv = df_ext[df_ext["tipo"].astype(str) == "02"].copy()
else:
    df_grao_serv = pd.DataFrame()

if not df_op_ext.empty and "origem" in df_op_ext.columns:
    df_ope_serv = df_op_ext[df_op_ext["origem"].astype(str) == "Servico"].copy()
else:
    df_ope_serv = pd.DataFrame()

# ===========================================================================
# Metricas gerais
# ===========================================================================
peso_apa_aguard = 0.0
peso_apa_disp = 0.0
peso_apa_uso = 0.0
qtd_apa_aguard = 0
qtd_apa_disp = 0
qtd_apa_uso = 0
if not df_aparas_serv.empty:
    df_aparas_serv["peso_kg"] = pd.to_numeric(df_aparas_serv["peso_kg"], errors="coerce").fillna(0)
    peso_apa_aguard = float(df_aparas_serv[df_aparas_serv["status"] == "aguardando_classificacao"]["peso_kg"].sum())
    peso_apa_disp = float(df_aparas_serv[df_aparas_serv["status"] == "disponivel"]["peso_kg"].sum())
    peso_apa_uso = float(df_aparas_serv[df_aparas_serv["status"] == "em_uso"]["peso_kg"].sum())
    qtd_apa_aguard = len(df_aparas_serv[df_aparas_serv["status"] == "aguardando_classificacao"])
    qtd_apa_disp = len(df_aparas_serv[df_aparas_serv["status"] == "disponivel"])
    qtd_apa_uso = len(df_aparas_serv[df_aparas_serv["status"] == "em_uso"])

peso_grao_analise = 0.0
peso_grao_disp = 0.0
qtd_grao_analise = 0
qtd_grao_disp = 0
if not df_grao_serv.empty:
    df_grao_serv["peso_kg"] = pd.to_numeric(df_grao_serv["peso_kg"], errors="coerce").fillna(0)
    peso_grao_analise = float(df_grao_serv[df_grao_serv["status"] == "em_analise"]["peso_kg"].sum())
    peso_grao_disp = float(df_grao_serv[df_grao_serv["status"] == "disponivel"]["peso_kg"].sum())
    qtd_grao_analise = len(df_grao_serv[df_grao_serv["status"] == "em_analise"])
    qtd_grao_disp = len(df_grao_serv[df_grao_serv["status"] == "disponivel"])

# ===========================================================================
# Tabs
# ===========================================================================
tab_aparas, tab_grao, tab_ope, tab_fechamento = st.tabs(["Aparas de Servico", "Grao de Servico", "OPEs de Servico", "Fechamento p/ Cliente"])

with tab_aparas:
    st.subheader("Aparas de Servico (Terceiros)")
    col_a1, col_a2, col_a3, col_a4 = st.columns(4)
    col_a1.metric("Aguardando Classif.", f"{qtd_apa_aguard} NF(s)", formatar_peso(peso_apa_aguard))
    col_a2.metric("Disponivel", f"{qtd_apa_disp} NF(s)", formatar_peso(peso_apa_disp))
    col_a3.metric("Em uso (OPE)", f"{qtd_apa_uso} NF(s)", formatar_peso(peso_apa_uso))
    col_a4.metric("**Total**", f"{qtd_apa_aguard + qtd_apa_disp + qtd_apa_uso} NF(s)",
                  formatar_peso(peso_apa_aguard + peso_apa_disp + peso_apa_uso))

    if df_aparas_serv.empty:
        st.info("Nenhuma apara de servico registrada.")
    else:
        cols = [c for c in ["numero_nf", "fornecedor", "qualidade", "tipo_fardo",
                            "quantidade", "peso_kg", "status", "opl_em_uso",
                            "data_recebimento", "data_classificacao"] if c in df_aparas_serv.columns]
        st.dataframe(df_aparas_serv[cols], use_container_width=True, hide_index=True)

with tab_grao:
    st.subheader("Grao de Servico (Tipo 02)")
    col_g1, col_g2, col_g3 = st.columns(3)
    col_g1.metric("Em Analise (Lab)", f"{qtd_grao_analise} lote(s)", formatar_peso(peso_grao_analise))
    col_g2.metric("Disponivel", f"{qtd_grao_disp} lote(s)", formatar_peso(peso_grao_disp))
    col_g3.metric("**Total**", f"{qtd_grao_analise + qtd_grao_disp} lote(s)",
                  formatar_peso(peso_grao_analise + peso_grao_disp))

    if df_grao_serv.empty:
        st.info("Nenhum grao de servico produzido.")
    else:
        cols = [c for c in ["codigo_lote", "data", "tipo_descricao", "extrusora",
                            "peso_kg", "status", "numero_op"] if c in df_grao_serv.columns]
        st.dataframe(df_grao_serv[cols], use_container_width=True, hide_index=True)

with tab_ope:
    st.subheader("OPEs de Servico")
    if df_ope_serv.empty:
        st.info("Nenhuma OPE de servico criada.")
    else:
        cols = [c for c in ["numero_op", "data", "cliente", "responsavel",
                            "volume_ton", "produto", "maquina", "status"] if c in df_ope_serv.columns]
        st.dataframe(df_ope_serv[cols], use_container_width=True, hide_index=True)

with tab_fechamento:
    st.subheader("Fechamento de OPE de Servico (Relatorio ao Cliente)")
    st.caption("Mostra peso entrada (aparas) vs peso saida (graos produzidos) com perdas do processo.")

    if df_ope_serv.empty:
        st.info("Nenhuma OPE de servico para fechar.")
    else:
        ope_opcoes = df_ope_serv["numero_op"].astype(str).tolist()
        ope_sel = st.selectbox("Selecione a OPE de Servico", options=ope_opcoes, key="serv_fech_ope")

        if ope_sel:
            ope_row = df_ope_serv[df_ope_serv["numero_op"].astype(str) == ope_sel].iloc[0]
            cliente_ope = str(ope_row.get("cliente", ""))
            data_ope = str(ope_row.get("data", ""))
            produto_ope = str(ope_row.get("produto", ""))

            st.markdown(f"**Cliente:** {cliente_ope} | **Data:** {formatar_data(data_ope)} | **Produto:** {produto_ope}")

            # Entrada: aparas usadas (opl_em_uso = numero_op)
            aparas_da_ope = pd.DataFrame()
            if not df_aparas_serv.empty:
                aparas_da_ope = df_aparas_serv[df_aparas_serv["opl_em_uso"].astype(str) == ope_sel].copy()

            peso_entrada = 0.0
            qtd_aparas = 0
            if not aparas_da_ope.empty:
                aparas_da_ope["peso_kg"] = pd.to_numeric(aparas_da_ope["peso_kg"], errors="coerce").fillna(0)
                peso_entrada = float(aparas_da_ope["peso_kg"].sum())
                qtd_aparas = len(aparas_da_ope)

            # Saida: lotes produzidos com numero_op = ope_sel
            lotes_da_ope = pd.DataFrame()
            if not df_grao_serv.empty:
                lotes_da_ope = df_grao_serv[df_grao_serv["numero_op"].astype(str) == ope_sel].copy()

            peso_saida = 0.0
            qtd_lotes = 0
            if not lotes_da_ope.empty:
                lotes_da_ope["peso_kg"] = pd.to_numeric(lotes_da_ope["peso_kg"], errors="coerce").fillna(0)
                peso_saida = float(lotes_da_ope["peso_kg"].sum())
                qtd_lotes = len(lotes_da_ope)

            perda_kg = max(0, peso_entrada - peso_saida)
            perda_perc = (perda_kg / peso_entrada * 100) if peso_entrada > 0 else 0

            st.divider()
            col_f1, col_f2, col_f3 = st.columns(3)
            col_f1.metric("Peso Entrada (Aparas)", formatar_peso(peso_entrada), f"{qtd_aparas} NF(s)")
            col_f2.metric("Peso Saida (Grao)", formatar_peso(peso_saida), f"{qtd_lotes} lote(s)")
            col_f3.metric("Perda do Processo", formatar_peso(perda_kg), f"{perda_perc:.2f}%")

            st.divider()
            st.markdown("#### Aparas Entradas")
            if aparas_da_ope.empty:
                st.caption("Nenhuma apara vinculada.")
            else:
                cols_ap = [c for c in ["numero_nf", "fornecedor", "qualidade", "tipo_fardo",
                                       "quantidade", "peso_kg"] if c in aparas_da_ope.columns]
                st.dataframe(aparas_da_ope[cols_ap], use_container_width=True, hide_index=True)

            st.markdown("#### Lotes Produzidos")
            if lotes_da_ope.empty:
                st.caption("Nenhum lote produzido ainda.")
            else:
                cols_lt = [c for c in ["codigo_lote", "data", "extrusora",
                                       "peso_kg", "status"] if c in lotes_da_ope.columns]
                st.dataframe(lotes_da_ope[cols_lt], use_container_width=True, hide_index=True)

            # Gerar relatorio Excel
            st.divider()
            from io import BytesIO
            def gerar_excel_servico():
                buf = BytesIO()
                with pd.ExcelWriter(buf, engine="openpyxl") as writer:
                    resumo = pd.DataFrame({
                        "Item": ["Cliente", "OPE", "Data", "Produto",
                                 "Peso Entrada (kg)", "Peso Saida (kg)",
                                 "Perda (kg)", "Perda (%)"],
                        "Valor": [cliente_ope, ope_sel, data_ope, produto_ope,
                                  f"{peso_entrada:.2f}", f"{peso_saida:.2f}",
                                  f"{perda_kg:.2f}", f"{perda_perc:.2f}%"],
                    })
                    resumo.to_excel(writer, sheet_name="Resumo", index=False)
                    if not aparas_da_ope.empty:
                        aparas_da_ope[cols_ap].to_excel(writer, sheet_name="Aparas Entrada", index=False)
                    if not lotes_da_ope.empty:
                        lotes_da_ope[cols_lt].to_excel(writer, sheet_name="Lotes Saida", index=False)
                return buf.getvalue()

            try:
                excel_bytes = gerar_excel_servico()
                st.download_button(
                    "Baixar Relatorio de Fechamento (Excel)",
                    excel_bytes,
                    file_name=f"fechamento_servico_{ope_sel}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    type="primary",
                    use_container_width=True,
                )
            except Exception as exc:
                st.error(f"Erro ao gerar relatorio: {exc}")
