import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta, time

from utils.database import read_sheet, read_sheet_no_cache, append_row
from utils.formatters import formatar_data, formatar_peso, TURNOS, TIPOS_PARADA

try:
    from utils.pdf_generator import gerar_pdf_producao_lavacao
except ImportError:
    gerar_pdf_producao_lavacao = None

# ---------------------------------------------------------------------------
# Titulo
# ---------------------------------------------------------------------------
st.header("Producao - Lavacao")

tab_lancamento, tab_paradas, tab_historico = st.tabs(["Lancamento", "Paradas", "Historico"])

# ===========================================================================
# Funcoes auxiliares
# ===========================================================================

def carregar_ops_abertas() -> list[str]:
    """Retorna lista de numeros de OPs com status 'aberta'."""
    try:
        df = read_sheet("op_lavacao")
        if df.empty:
            return []
        abertas = df[df["status"].astype(str).str.lower() == "aberta"]
        if abertas.empty:
            return []
        return abertas["numero_op"].astype(str).tolist()
    except Exception:
        return []


# ===========================================================================
# TAB: Lancamento
# ===========================================================================
with tab_lancamento:
    st.subheader("Lancamento de Producao Diaria")

    ops_abertas = carregar_ops_abertas()

    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1:
        data_prod = st.date_input("Data", value=date.today(), key="data_lancamento")
    with col_sel2:
        turno = st.selectbox("Turno", options=TURNOS, key="turno_lancamento")
    with col_sel3:
        if ops_abertas:
            numero_op = st.selectbox("Numero da OP", options=ops_abertas, key="op_lancamento")
        else:
            st.warning("Nenhuma OP aberta encontrada.")
            numero_op = st.text_input("Numero da OP (manual)", key="op_lancamento_manual")

    st.divider()

    # -----------------------------------------------------------------------
    # Secao: Fardinhos
    # -----------------------------------------------------------------------
    st.subheader("Fardinhos")
    with st.form("form_fardinhos", clear_on_submit=True):
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            nf_fardinho = st.text_input("NF", key="nf_fardinho")
        with col_f2:
            qtd_fardinho = st.number_input("Quantidade", min_value=0, step=1, key="qtd_fardinho")
        with col_f3:
            peso_fardinho = st.number_input("Peso (kg)", min_value=0.0, step=0.5, format="%.1f", key="peso_fardinho")

        submit_fardinho = st.form_submit_button("Registrar Fardinho", type="primary", use_container_width=True)

    if submit_fardinho:
        erros = []
        if not nf_fardinho.strip():
            erros.append("NF e obrigatoria.")
        if qtd_fardinho <= 0:
            erros.append("Quantidade deve ser maior que zero.")
        if peso_fardinho <= 0:
            erros.append("Peso deve ser maior que zero.")
        op_val = numero_op if ops_abertas else numero_op
        if not op_val:
            erros.append("Numero da OP e obrigatorio.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            try:
                dados_fardinho = {
                    "data": data_prod.isoformat(),
                    "turno": turno,
                    "numero_op": op_val,
                    "tipo_fardo": "fardinho",
                    "nf": nf_fardinho.strip(),
                    "quantidade": qtd_fardinho,
                    "peso_kg": peso_fardinho,
                    "perda_lixo_kg": 0,
                    "perda_papelao_kg": 0,
                    "perda_plastico_colorido_kg": 0,
                    "perda_total_kg": 0,
                    "registrado_por": "",
                }
                append_row("producao_lavacao", dados_fardinho)
                st.toast("Fardinho registrado com sucesso!")
                st.success(f"Fardinho NF **{nf_fardinho}** registrado.")

                # Botao para baixar PDF da producao do dia/turno
                if gerar_pdf_producao_lavacao is not None:
                    try:
                        data_str = data_prod.isoformat()
                        df_reg = read_sheet_no_cache("producao_lavacao")
                        df_par = read_sheet_no_cache("paradas_lavacao")
                        registros_list = []
                        paradas_list = []
                        if not df_reg.empty:
                            registros_list = df_reg[
                                (df_reg["data"] == data_str) & (df_reg["turno"] == turno)
                            ].to_dict("records")
                        if not df_par.empty:
                            paradas_list = df_par[
                                (df_par["data"] == data_str) & (df_par["turno"] == turno)
                            ].to_dict("records")
                        pdf_bytes = gerar_pdf_producao_lavacao(
                            data_str, turno, registros_list, paradas_list
                        )
                        st.download_button(
                            "Baixar PDF da Producao",
                            pdf_bytes,
                            file_name=f"producao_lavacao_{data_str}_{turno}.pdf",
                            mime="application/pdf",
                            key="pdf_fardinho",
                        )
                    except Exception:
                        pass
            except Exception as exc:
                st.error(f"Erro ao registrar fardinho: {exc}")

    st.divider()

    # -----------------------------------------------------------------------
    # Secao: Fardoes
    # -----------------------------------------------------------------------
    st.subheader("Fardoes")
    with st.form("form_fardoes", clear_on_submit=True):
        col_g1, col_g2, col_g3 = st.columns(3)
        with col_g1:
            nf_fardao = st.text_input("NF", key="nf_fardao")
        with col_g2:
            qtd_fardao = st.number_input("Quantidade", min_value=0, step=1, key="qtd_fardao")
        with col_g3:
            peso_fardao = st.number_input("Peso (kg)", min_value=0.0, step=0.5, format="%.1f", key="peso_fardao")

        submit_fardao = st.form_submit_button("Registrar Fardao", type="primary", use_container_width=True)

    if submit_fardao:
        erros = []
        if not nf_fardao.strip():
            erros.append("NF e obrigatoria.")
        if qtd_fardao <= 0:
            erros.append("Quantidade deve ser maior que zero.")
        if peso_fardao <= 0:
            erros.append("Peso deve ser maior que zero.")
        op_val = numero_op if ops_abertas else numero_op
        if not op_val:
            erros.append("Numero da OP e obrigatorio.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            try:
                dados_fardao = {
                    "data": data_prod.isoformat(),
                    "turno": turno,
                    "numero_op": op_val,
                    "tipo_fardo": "fardao",
                    "nf": nf_fardao.strip(),
                    "quantidade": qtd_fardao,
                    "peso_kg": peso_fardao,
                    "perda_lixo_kg": 0,
                    "perda_papelao_kg": 0,
                    "perda_plastico_colorido_kg": 0,
                    "perda_total_kg": 0,
                    "registrado_por": "",
                }
                append_row("producao_lavacao", dados_fardao)
                st.toast("Fardao registrado com sucesso!")
                st.success(f"Fardao NF **{nf_fardao}** registrado.")

                # Botao para baixar PDF da producao do dia/turno
                if gerar_pdf_producao_lavacao is not None:
                    try:
                        data_str = data_prod.isoformat()
                        df_reg = read_sheet_no_cache("producao_lavacao")
                        df_par = read_sheet_no_cache("paradas_lavacao")
                        registros_list = []
                        paradas_list = []
                        if not df_reg.empty:
                            registros_list = df_reg[
                                (df_reg["data"] == data_str) & (df_reg["turno"] == turno)
                            ].to_dict("records")
                        if not df_par.empty:
                            paradas_list = df_par[
                                (df_par["data"] == data_str) & (df_par["turno"] == turno)
                            ].to_dict("records")
                        pdf_bytes = gerar_pdf_producao_lavacao(
                            data_str, turno, registros_list, paradas_list
                        )
                        st.download_button(
                            "Baixar PDF da Producao",
                            pdf_bytes,
                            file_name=f"producao_lavacao_{data_str}_{turno}.pdf",
                            mime="application/pdf",
                            key="pdf_fardao",
                        )
                    except Exception:
                        pass
            except Exception as exc:
                st.error(f"Erro ao registrar fardao: {exc}")

    st.divider()

    # -----------------------------------------------------------------------
    # Secao: Separacao / Perdas
    # -----------------------------------------------------------------------
    st.subheader("Separacao / Perdas")

    with st.form("form_perdas", clear_on_submit=True):
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            perda_lixo = st.number_input("Perda Lixo (kg)", min_value=0.0, step=0.1, format="%.1f", key="perda_lixo")
        with col_p2:
            perda_papelao = st.number_input("Perda Papelao (kg)", min_value=0.0, step=0.1, format="%.1f", key="perda_papelao")
        with col_p3:
            perda_plastico = st.number_input("Perda Plastico Colorido (kg)", min_value=0.0, step=0.1, format="%.1f", key="perda_plastico")

        perda_total = perda_lixo + perda_papelao + perda_plastico

        registrado_por = st.text_input("Registrado por", key="registrado_por_perdas")

        submit_perdas = st.form_submit_button("Registrar Perdas", use_container_width=True)

    # Mostrar metrica fora do form (usa valores do form)
    st.metric("Perda Total", formatar_peso(perda_lixo + perda_papelao + perda_plastico))

    if submit_perdas:
        erros = []
        if perda_total <= 0:
            erros.append("Informe ao menos um tipo de perda.")
        if not registrado_por.strip():
            erros.append("Campo 'Registrado por' e obrigatorio.")
        op_val = numero_op if ops_abertas else numero_op
        if not op_val:
            erros.append("Numero da OP e obrigatorio.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            try:
                dados_perdas = {
                    "data": data_prod.isoformat(),
                    "turno": turno,
                    "numero_op": op_val,
                    "tipo_fardo": "perdas",
                    "nf": "",
                    "quantidade": 0,
                    "peso_kg": 0,
                    "perda_lixo_kg": perda_lixo,
                    "perda_papelao_kg": perda_papelao,
                    "perda_plastico_colorido_kg": perda_plastico,
                    "perda_total_kg": perda_total,
                    "registrado_por": registrado_por.strip(),
                }
                append_row("producao_lavacao", dados_perdas)
                st.toast("Perdas registradas com sucesso!")
                st.success(f"Perdas registradas - Total: {formatar_peso(perda_total)}")

                # Botao para baixar PDF da producao do dia/turno
                if gerar_pdf_producao_lavacao is not None:
                    try:
                        data_str = data_prod.isoformat()
                        df_reg = read_sheet_no_cache("producao_lavacao")
                        df_par = read_sheet_no_cache("paradas_lavacao")
                        registros_list = []
                        paradas_list = []
                        if not df_reg.empty:
                            registros_list = df_reg[
                                (df_reg["data"] == data_str) & (df_reg["turno"] == turno)
                            ].to_dict("records")
                        if not df_par.empty:
                            paradas_list = df_par[
                                (df_par["data"] == data_str) & (df_par["turno"] == turno)
                            ].to_dict("records")
                        pdf_bytes = gerar_pdf_producao_lavacao(
                            data_str, turno, registros_list, paradas_list
                        )
                        st.download_button(
                            "Baixar PDF da Producao",
                            pdf_bytes,
                            file_name=f"producao_lavacao_{data_str}_{turno}.pdf",
                            mime="application/pdf",
                            key="pdf_perdas",
                        )
                    except Exception:
                        pass
            except Exception as exc:
                st.error(f"Erro ao registrar perdas: {exc}")


# ===========================================================================
# TAB: Paradas
# ===========================================================================
with tab_paradas:
    st.subheader("Registro de Paradas")

    with st.form("form_parada", clear_on_submit=True):
        col_par1, col_par2 = st.columns(2)
        with col_par1:
            data_parada = st.date_input("Data", value=date.today(), key="data_parada")
            turno_parada = st.selectbox("Turno", options=TURNOS, key="turno_parada")
            tipo_parada = st.selectbox("Tipo de Parada", options=TIPOS_PARADA, key="tipo_parada")
        with col_par2:
            hora_inicio = st.time_input("Hora Inicio", value=time(8, 0), key="hora_inicio_parada")
            hora_fim = st.time_input("Hora Fim", value=time(8, 30), key="hora_fim_parada")
            observacao_parada = st.text_area("Observacao", key="obs_parada")

        submit_parada = st.form_submit_button("Registrar Parada", type="primary", use_container_width=True)

    if submit_parada:
        # Calcular duracao em minutos
        dt_inicio = datetime.combine(data_parada, hora_inicio)
        dt_fim = datetime.combine(data_parada, hora_fim)

        # Se hora_fim < hora_inicio, assume que cruzou meia-noite
        if dt_fim <= dt_inicio:
            dt_fim += timedelta(days=1)

        duracao_min = int((dt_fim - dt_inicio).total_seconds() / 60)

        erros = []
        if duracao_min <= 0:
            erros.append("Duracao da parada deve ser maior que zero.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            try:
                dados_parada = {
                    "data": data_parada.isoformat(),
                    "turno": turno_parada,
                    "tipo_parada": tipo_parada,
                    "hora_inicio": hora_inicio.strftime("%H:%M"),
                    "hora_fim": hora_fim.strftime("%H:%M"),
                    "duracao_min": duracao_min,
                    "observacao": observacao_parada.strip(),
                }
                append_row("paradas_lavacao", dados_parada)
                st.toast("Parada registrada com sucesso!")
                st.success(f"Parada registrada: **{tipo_parada}** - Duracao: {duracao_min} minutos")
            except Exception as exc:
                st.error(f"Erro ao registrar parada: {exc}")

    # Exibir paradas recentes
    st.divider()
    st.subheader("Paradas Recentes")
    try:
        df_paradas = read_sheet("paradas_lavacao")
        if df_paradas.empty:
            st.info("Nenhuma parada registrada.")
        else:
            df_paradas["data"] = df_paradas["data"].apply(formatar_data)
            st.dataframe(
                df_paradas[["data", "turno", "tipo_parada", "hora_inicio", "hora_fim", "duracao_min", "observacao"]],
                use_container_width=True,
                hide_index=True,
            )
    except Exception as exc:
        st.error(f"Erro ao carregar paradas: {exc}")


# ===========================================================================
# TAB: Historico
# ===========================================================================
with tab_historico:
    st.subheader("Historico de Producao - Lavacao")

    # Filtros
    col_h1, col_h2, col_h3 = st.columns(3)
    with col_h1:
        hist_data_inicio = st.date_input(
            "Data Inicio",
            value=date.today() - timedelta(days=30),
            key="hist_data_inicio",
        )
    with col_h2:
        hist_data_fim = st.date_input(
            "Data Fim",
            value=date.today(),
            key="hist_data_fim",
        )
    with col_h3:
        hist_turno = st.selectbox(
            "Turno",
            options=["Todos"] + TURNOS,
            key="hist_turno",
        )

    try:
        df_hist = read_sheet("producao_lavacao")
    except Exception as exc:
        st.error(f"Erro ao carregar historico: {exc}")
        df_hist = pd.DataFrame()

    if df_hist.empty:
        st.info("Nenhum registro de producao encontrado.")
    else:
        # Filtrar por data
        df_hist["data_dt"] = pd.to_datetime(df_hist["data"], errors="coerce").dt.date
        mask = (df_hist["data_dt"] >= hist_data_inicio) & (df_hist["data_dt"] <= hist_data_fim)
        df_filtrado = df_hist[mask].copy()

        # Filtrar por turno
        if hist_turno != "Todos":
            df_filtrado = df_filtrado[df_filtrado["turno"] == hist_turno]

        if df_filtrado.empty:
            st.info("Nenhum registro encontrado para os filtros selecionados.")
        else:
            # Converter colunas numericas
            for col_num in ["quantidade", "peso_kg", "perda_lixo_kg", "perda_papelao_kg",
                            "perda_plastico_colorido_kg", "perda_total_kg"]:
                if col_num in df_filtrado.columns:
                    df_filtrado[col_num] = pd.to_numeric(df_filtrado[col_num], errors="coerce").fillna(0)

            # Metricas resumo
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)

            total_registros = len(df_filtrado[df_filtrado["tipo_fardo"].isin(["fardinho", "fardao"])])
            total_peso = df_filtrado[df_filtrado["tipo_fardo"].isin(["fardinho", "fardao"])]["peso_kg"].sum()
            total_perdas = df_filtrado["perda_total_kg"].sum()
            total_fardinhos = len(df_filtrado[df_filtrado["tipo_fardo"] == "fardinho"])
            total_fardoes = len(df_filtrado[df_filtrado["tipo_fardo"] == "fardao"])

            with col_m1:
                st.metric("Total Registros", total_registros)
            with col_m2:
                st.metric("Peso Total", formatar_peso(total_peso))
            with col_m3:
                st.metric("Perdas Total", formatar_peso(total_perdas))
            with col_m4:
                st.metric("Fardinhos / Fardoes", f"{total_fardinhos} / {total_fardoes}")

            st.divider()

            # Tabela de dados
            colunas_exibir = ["data", "turno", "numero_op", "tipo_fardo", "nf",
                              "quantidade", "peso_kg", "perda_lixo_kg", "perda_papelao_kg",
                              "perda_plastico_colorido_kg", "perda_total_kg", "registrado_por"]
            colunas_presentes = [c for c in colunas_exibir if c in df_filtrado.columns]
            df_exibir = df_filtrado[colunas_presentes].copy()
            df_exibir["data"] = df_exibir["data"].apply(formatar_data)

            st.dataframe(df_exibir, use_container_width=True, hide_index=True)
