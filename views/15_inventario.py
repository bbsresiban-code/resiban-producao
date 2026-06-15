import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date
from io import BytesIO

from utils.database import read_sheet
from utils.formatters import formatar_peso, formatar_data, fardos_breakdown

st.header("Inventario Geral")
st.caption("Visao consolidada de aparas (materia-prima) e grao (produto acabado) PROPRIOS.")
st.caption("Materiais de Servico (terceiros) NAO entram aqui - veja na aba 'Controle Servico'.")

try:
    df_aparas = read_sheet("aparas_estoque")
except Exception:
    df_aparas = pd.DataFrame()

try:
    df_ext = read_sheet("producao_extrusao")
except Exception:
    df_ext = pd.DataFrame()

try:
    df_qual = read_sheet("qualidade")
except Exception:
    df_qual = pd.DataFrame()

# ===========================================================================
# Aparas
# ===========================================================================
aparas_aguardando = 0.0
aparas_disponivel = 0.0
aparas_em_uso = 0.0
qtd_aguardando = 0
qtd_disponivel = 0
qtd_em_uso = 0

if not df_aparas.empty:
    if "tipo_material" in df_aparas.columns:
        df_aparas = df_aparas[
            (df_aparas["tipo_material"].astype(str) == "Proprio")
            | (df_aparas["tipo_material"].isna())
            | (df_aparas["tipo_material"].astype(str) == "")
        ].copy()

if not df_aparas.empty:
    df_aparas["peso_kg"] = pd.to_numeric(df_aparas["peso_kg"], errors="coerce").fillna(0)
    df_aparas["qtd_fardao"] = df_aparas.apply(lambda r: fardos_breakdown(r)[0], axis=1)
    df_aparas["qtd_fardinho"] = df_aparas.apply(lambda r: fardos_breakdown(r)[1], axis=1)
    aparas_aguardando = float(df_aparas[df_aparas["status"] == "aguardando_classificacao"]["peso_kg"].sum())
    aparas_disponivel = float(df_aparas[df_aparas["status"] == "disponivel"]["peso_kg"].sum())
    aparas_em_uso = float(df_aparas[df_aparas["status"] == "em_uso"]["peso_kg"].sum())
    qtd_aguardando = len(df_aparas[df_aparas["status"] == "aguardando_classificacao"])
    qtd_disponivel = len(df_aparas[df_aparas["status"] == "disponivel"])
    qtd_em_uso = len(df_aparas[df_aparas["status"] == "em_uso"])

total_aparas = aparas_aguardando + aparas_disponivel + aparas_em_uso
total_qtd_aparas = qtd_aguardando + qtd_disponivel + qtd_em_uso

st.subheader("Aparas (Materia-Prima)")
col_a1, col_a2, col_a3, col_a4 = st.columns(4)
col_a1.metric("Aguardando Classif.", f"{qtd_aguardando} NF(s)", formatar_peso(aparas_aguardando))
col_a2.metric("Disponivel", f"{qtd_disponivel} NF(s)", formatar_peso(aparas_disponivel))
col_a3.metric("Em uso (OPL)", f"{qtd_em_uso} NF(s)", formatar_peso(aparas_em_uso))
col_a4.metric("**Total Aparas**", f"{total_qtd_aparas} NF(s)", formatar_peso(total_aparas))

# Breakdown por qualidade
if not df_aparas.empty:
    df_disp_q = df_aparas[df_aparas["status"] == "disponivel"]
    if not df_disp_q.empty:
        st.markdown("**Aparas disponiveis por Qualidade:**")
        por_qual = df_disp_q.groupby("qualidade").agg(
            qtd=("numero_nf", "count"),
            fardoes=("qtd_fardao", "sum"),
            fardinhos=("qtd_fardinho", "sum"),
            peso=("peso_kg", "sum"),
        ).reset_index()
        por_qual.columns = ["Qualidade", "Qtd NFs", "Fardoes", "Fardinhos", "Peso (kg)"]
        por_qual["Peso (kg)"] = por_qual["Peso (kg)"].apply(formatar_peso)
        st.dataframe(por_qual, use_container_width=True, hide_index=True)

# ===========================================================================
# Grao (Produto Acabado)
# ===========================================================================
st.divider()
st.subheader("Grao (Produto Acabado)")

grao_em_analise = 0.0
grao_disponivel = 0.0
qtd_grao_analise = 0
qtd_grao_disp = 0

if not df_ext.empty:
    if "tipo" in df_ext.columns:
        df_ext = df_ext[df_ext["tipo"].astype(str) != "02"].copy()
    df_ext["peso_kg"] = pd.to_numeric(df_ext["peso_kg"], errors="coerce").fillna(0)
    df_grao_analise = df_ext[df_ext["status"] == "em_analise"]
    df_grao_disp = df_ext[df_ext["status"] == "disponivel"]
    grao_em_analise = float(df_grao_analise["peso_kg"].sum())
    grao_disponivel = float(df_grao_disp["peso_kg"].sum())
    qtd_grao_analise = len(df_grao_analise)
    qtd_grao_disp = len(df_grao_disp)

total_grao = grao_em_analise + grao_disponivel
total_qtd_grao = qtd_grao_analise + qtd_grao_disp

col_g1, col_g2, col_g3 = st.columns(3)
col_g1.metric("Em Analise (Lab)", f"{qtd_grao_analise} lote(s)", formatar_peso(grao_em_analise))
col_g2.metric("Disponivel", f"{qtd_grao_disp} lote(s)", formatar_peso(grao_disponivel))
col_g3.metric("**Total Grao**", f"{total_qtd_grao} lote(s)", formatar_peso(total_grao))

# Breakdown grao por grade
if not df_ext.empty and not df_qual.empty:
    disp = df_ext[df_ext["status"] == "disponivel"]
    if not disp.empty and "codigo_lote" in disp.columns and "codigo_lote" in df_qual.columns:
        merged = disp.merge(df_qual[["codigo_lote", "grade"]], on="codigo_lote", how="left")
        merged["peso_kg"] = pd.to_numeric(merged["peso_kg"], errors="coerce").fillna(0)
        por_grade = merged.groupby("grade").agg(
            qtd=("codigo_lote", "count"),
            peso=("peso_kg", "sum"),
        ).reset_index()
        por_grade = por_grade[por_grade["grade"].notna() & (por_grade["grade"] != "")]
        if not por_grade.empty:
            st.markdown("**Grao disponivel por Grade:**")
            por_grade.columns = ["Grade", "Qtd Lotes", "Peso (kg)"]
            por_grade["Peso (kg)"] = por_grade["Peso (kg)"].apply(formatar_peso)
            st.dataframe(por_grade, use_container_width=True, hide_index=True)

# ===========================================================================
# Total geral
# ===========================================================================
st.divider()
st.subheader("Resumo Geral do Inventario")
col_r1, col_r2, col_r3 = st.columns(3)
col_r1.metric("Total Aparas", formatar_peso(total_aparas))
col_r2.metric("Total Grao", formatar_peso(total_grao))
col_r3.metric("**Inventario Total**", formatar_peso(total_aparas + total_grao))

# ===========================================================================
# Export Excel
# ===========================================================================
st.divider()
st.subheader("Exportar Relatorio")

def gerar_excel_inventario():
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        resumo = pd.DataFrame({
            "Categoria": ["Aparas Aguardando", "Aparas Disponivel", "Aparas Em Uso (OPL)", "Total Aparas",
                          "Grao Em Analise", "Grao Disponivel", "Total Grao", "INVENTARIO TOTAL"],
            "Qtd": [qtd_aguardando, qtd_disponivel, qtd_em_uso, total_qtd_aparas,
                    qtd_grao_analise, qtd_grao_disp, total_qtd_grao, total_qtd_aparas + total_qtd_grao],
            "Peso (kg)": [aparas_aguardando, aparas_disponivel, aparas_em_uso, total_aparas,
                          grao_em_analise, grao_disponivel, total_grao, total_aparas + total_grao],
        })
        resumo.to_excel(writer, sheet_name="Resumo", index=False)

        if not df_aparas.empty:
            cols_ap = [c for c in ["numero_nf", "fornecedor", "qualidade", "tipo_fardo",
                                   "qtd_fardao", "qtd_fardinho", "quantidade", "peso_kg",
                                   "status", "opl_em_uso",
                                   "data_recebimento", "data_classificacao"] if c in df_aparas.columns]
            df_aparas[cols_ap].to_excel(writer, sheet_name="Aparas Detalhado", index=False)

        if not df_ext.empty:
            df_grao_full = df_ext[df_ext["status"].isin(["em_analise", "disponivel"])]
            if not df_grao_full.empty:
                if not df_qual.empty and "codigo_lote" in df_qual.columns:
                    df_grao_full = df_grao_full.merge(
                        df_qual[["codigo_lote", "grade", "cor"]], on="codigo_lote", how="left"
                    )
                cols_gr = [c for c in ["codigo_lote", "data", "tipo_descricao", "extrusora",
                                       "peso_kg", "status", "grade", "cor", "opl_origem"] if c in df_grao_full.columns]
                df_grao_full[cols_gr].to_excel(writer, sheet_name="Grao Detalhado", index=False)
    return buffer.getvalue()

try:
    excel_bytes = gerar_excel_inventario()
    st.download_button(
        "Baixar Relatorio Inventario (Excel)",
        excel_bytes,
        file_name=f"inventario_{date.today().isoformat()}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
        use_container_width=True,
    )
except Exception as exc:
    st.error(f"Erro ao gerar relatorio: {exc}")
