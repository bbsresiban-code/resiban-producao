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

tab_lancamento, tab_paradas, tab_historico = st.tabs(
    ["Lancamento", "Paradas", "Historico"]
)


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


def carregar_nfs_da_op(numero_op: str) -> list[dict]:
    """Retorna lista de dicts com dados das NFs vinculadas a OP informada."""
    try:
        df_ops = read_sheet("op_lavacao")
        df_nfs_all = read_sheet("op_lavacao_nfs")
        if df_ops.empty or df_nfs_all.empty:
            return []
        op_row = df_ops[df_ops["numero_op"].astype(str) == str(numero_op)]
        if op_row.empty:
            return []
        op_id = str(op_row.iloc[0]["id"])
        nfs_desta_op = df_nfs_all[df_nfs_all["op_lavacao_id"].astype(str) == op_id]
        if nfs_desta_op.empty:
            return []
        resultado = []
        for _, row in nfs_desta_op.iterrows():
            tipo = str(row.get("tipo_fardo", "")).strip()
            if tipo.lower() not in ("fardinho", "fardao"):
                tipo = "Fardinho"
            else:
                tipo = tipo.capitalize()
            resultado.append({
                "nf_apara": str(row.get("nf_apara", "")),
                "fornecedor": str(row.get("fornecedor", "")),
                "tipo_fardo": tipo,
                "quant_fardos": int(float(row.get("quant_fardos", 0) or 0)),
                "peso_kg": float(row.get("peso_kg", 0) or 0),
            })
        return resultado
    except Exception:
        return []


def carregar_producao_existente(numero_op: str) -> pd.DataFrame:
    """Retorna DataFrame com registros de producao_lavacao da OP (sem perdas)."""
    try:
        df = read_sheet_no_cache("producao_lavacao")
        if df.empty:
            return pd.DataFrame()
        df = df[df["numero_op"].astype(str) == str(numero_op)]
        df = df[df["tipo_fardo"].astype(str).str.lower() != "perdas"]
        for col in ("quantidade", "peso_kg"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
        return df
    except Exception:
        return pd.DataFrame()


# ===========================================================================
# TAB: Lancamento
# ===========================================================================
with tab_lancamento:
    st.subheader("Lancamento de Producao Diaria")

    ops_abertas = carregar_ops_abertas()

    usuario_logado = st.session_state.get("usuario", "master")
    perfil_logado = st.session_state.get("perfil", "master")

    if perfil_logado == "turno":
        turno_fixo = usuario_logado[-1].upper()
    else:
        turno_fixo = None

    col_sel1, col_sel2, col_sel3 = st.columns(3)
    with col_sel1:
        data_prod = st.date_input("Data", value=date.today(), key="data_lancamento")
    with col_sel2:
        if turno_fixo:
            turno = turno_fixo
            st.info(f"Turno: **{turno}**")
        else:
            turno = st.selectbox("Turno", options=TURNOS, key="turno_lancamento")
    with col_sel3:
        if ops_abertas:
            numero_op = st.selectbox(
                "Numero da OP", options=ops_abertas, key="op_lancamento"
            )
        else:
            st.warning("Nenhuma OP aberta encontrada.")
            numero_op = None

    # -------------------------------------------------------------------
    # Carregar NFs da OP e producao existente
    # -------------------------------------------------------------------
    nfs_da_op: list[dict] = []
    df_prod_existente = pd.DataFrame()

    if numero_op:
        nfs_da_op = carregar_nfs_da_op(numero_op)
        df_prod_existente = carregar_producao_existente(numero_op)

    if numero_op and not nfs_da_op:
        st.warning(
            "Nenhuma NF cadastrada nesta OP. Cadastre as NFs na tela de OP Lavacao."
        )

    st.divider()

    # -------------------------------------------------------------------
    # Para cada NF, mostrar card com planejado / lancado / restante
    # -------------------------------------------------------------------
    if numero_op and nfs_da_op:
        for idx_nf, nf_info in enumerate(nfs_da_op):
            nf_numero = nf_info["nf_apara"]
            nf_fornec = nf_info["fornecedor"]
            nf_tipo = nf_info["tipo_fardo"]
            nf_qtd_plan = nf_info["quant_fardos"]
            nf_peso_plan = nf_info["peso_kg"]

            st.subheader(f"NF {nf_numero} - {nf_fornec} ({nf_tipo})")

            # Calcular ja lancado para esta NF
            qtd_lancada = 0
            peso_lancado = 0.0
            if not df_prod_existente.empty:
                mask_nf = df_prod_existente["nf"].astype(str) == nf_numero
                if mask_nf.any():
                    qtd_lancada = int(df_prod_existente.loc[mask_nf, "quantidade"].sum())
                    peso_lancado = float(df_prod_existente.loc[mask_nf, "peso_kg"].sum())

            qtd_restante = max(0, nf_qtd_plan - qtd_lancada)
            peso_restante = max(0.0, nf_peso_plan - peso_lancado)

            col_m1, col_m2, col_m3 = st.columns(3)
            with col_m1:
                st.metric(
                    "Planejado",
                    f"{nf_qtd_plan} un / {formatar_peso(nf_peso_plan)}",
                )
            with col_m2:
                st.metric(
                    "Ja Lancado",
                    f"{qtd_lancada} un / {formatar_peso(peso_lancado)}",
                )
            with col_m3:
                st.metric(
                    "Restante",
                    f"{qtd_restante} un / {formatar_peso(peso_restante)}",
                )

            if qtd_restante > 0 and peso_restante > 0:
                with st.form(
                    f"form_nf_{idx_nf}_{nf_numero}", clear_on_submit=True
                ):
                    col_f1, col_f2 = st.columns(2)
                    with col_f1:
                        quantidade = st.number_input(
                            "Quantidade",
                            min_value=0,
                            max_value=qtd_restante,
                            step=1,
                            key=f"qtd_nf_{idx_nf}",
                            value=None,
                        )
                    with col_f2:
                        peso_kg = st.number_input(
                            "Peso (kg)",
                            min_value=0.0,
                            max_value=float(peso_restante),
                            step=0.5,
                            format="%.1f",
                            key=f"peso_nf_{idx_nf}",
                            value=None,
                        )
                    submit_nf = st.form_submit_button(
                        f"Registrar {nf_tipo}",
                        type="primary",
                        use_container_width=True,
                    )

                if submit_nf:
                    erros = []
                    if not quantidade or quantidade <= 0:
                        erros.append("Quantidade deve ser maior que zero.")
                    if not peso_kg or peso_kg <= 0:
                        erros.append("Peso deve ser maior que zero.")
                    if erros:
                        for e in erros:
                            st.error(e)
                    else:
                        try:
                            dados = {
                                "data": data_prod.isoformat(),
                                "turno": turno,
                                "numero_op": numero_op,
                                "tipo_fardo": nf_tipo.lower(),
                                "nf": nf_numero,
                                "quantidade": int(quantidade or 0),
                                "peso_kg": float(peso_kg or 0),
                                "perda_lixo_kg": 0,
                                "perda_papelao_kg": 0,
                                "perda_plastico_colorido_kg": 0,
                                "perda_total_kg": 0,
                                "registrado_por": "",
                            }
                            append_row("producao_lavacao", dados)
                            st.toast(f"{nf_tipo} registrado com sucesso!")
                            st.success(
                                f"{nf_tipo} NF **{nf_numero}** - "
                                f"{int(quantidade or 0)} un / {formatar_peso(float(peso_kg or 0))} registrado."
                            )
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erro ao registrar producao: {exc}")
            else:
                st.success("NF totalmente consumida.")

            st.divider()

    # -------------------------------------------------------------------
    # Secao: Separacao / Perdas
    # -------------------------------------------------------------------
    if numero_op:
        st.subheader("Separacao / Perdas")
        st.caption(
            "Perdas sao derivadas do material ja pesado como entrada. "
            "Nao sao somadas ao peso de producao."
        )

        with st.form("form_perdas", clear_on_submit=True):
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1:
                perda_lixo = st.number_input(
                    "Perda Lixo (kg)",
                    min_value=0.0,
                    step=0.1,
                    format="%.1f",
                    key="perda_lixo",
                    value=None,
                )
            with col_p2:
                perda_papelao = st.number_input(
                    "Perda Papelao (kg)",
                    min_value=0.0,
                    step=0.1,
                    format="%.1f",
                    key="perda_papelao",
                    value=None,
                )
            with col_p3:
                perda_plastico = st.number_input(
                    "Perda Plastico Colorido (kg)",
                    min_value=0.0,
                    step=0.1,
                    format="%.1f",
                    key="perda_plastico",
                    value=None,
                )

            registrado_por = st.text_input(
                "Registrado por", key="registrado_por_perdas"
            )

            submit_perdas = st.form_submit_button(
                "Registrar Perdas", use_container_width=True
            )

        perda_total_display = (perda_lixo or 0) + (perda_papelao or 0) + (perda_plastico or 0)
        st.metric("Perda Total", formatar_peso(perda_total_display))

        if submit_perdas:
            perda_total = (perda_lixo or 0) + (perda_papelao or 0) + (perda_plastico or 0)
            erros = []
            if perda_total <= 0:
                erros.append("Informe ao menos um tipo de perda.")
            if not registrado_por.strip():
                erros.append("Campo 'Registrado por' e obrigatorio.")
            if erros:
                for e in erros:
                    st.error(e)
            else:
                try:
                    dados_perdas = {
                        "data": data_prod.isoformat(),
                        "turno": turno,
                        "numero_op": numero_op,
                        "tipo_fardo": "perdas",
                        "nf": "",
                        "quantidade": 0,
                        "peso_kg": 0,
                        "perda_lixo_kg": float(perda_lixo or 0),
                        "perda_papelao_kg": float(perda_papelao or 0),
                        "perda_plastico_colorido_kg": float(perda_plastico or 0),
                        "perda_total_kg": perda_total,
                        "registrado_por": registrado_por.strip(),
                    }
                    append_row("producao_lavacao", dados_perdas)
                    st.toast("Perdas registradas com sucesso!")
                    st.success(
                        f"Perdas registradas - Total: {formatar_peso(perda_total)}"
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"Erro ao registrar perdas: {exc}")

        st.divider()

    # -------------------------------------------------------------------
    # Secao: Relatorio do Turno (PDF consolidado)
    # -------------------------------------------------------------------
    if numero_op:
        st.subheader("Relatorio do Turno")

        data_str = data_prod.isoformat()

        try:
            df_turno = read_sheet_no_cache("producao_lavacao")
            df_paradas_turno = read_sheet_no_cache("paradas_lavacao")
        except Exception:
            df_turno = pd.DataFrame()
            df_paradas_turno = pd.DataFrame()

        # Filtrar registros do dia + turno
        registros_turno = []
        if not df_turno.empty:
            mask_turno = (
                (df_turno["data"].astype(str) == data_str)
                & (df_turno["turno"].astype(str) == turno)
            )
            df_turno_filtrado = df_turno[mask_turno].copy()
            if not df_turno_filtrado.empty:
                registros_turno = df_turno_filtrado.to_dict("records")

        paradas_turno = []
        if not df_paradas_turno.empty:
            mask_par = (
                (df_paradas_turno["data"].astype(str) == data_str)
                & (df_paradas_turno["turno"].astype(str) == turno)
            )
            df_par_filtrado = df_paradas_turno[mask_par].copy()
            if not df_par_filtrado.empty:
                paradas_turno = df_par_filtrado.to_dict("records")

        if registros_turno:
            # Resumo do turno
            df_resumo = pd.DataFrame(registros_turno)
            for col_num in ("quantidade", "peso_kg", "perda_total_kg"):
                if col_num in df_resumo.columns:
                    df_resumo[col_num] = pd.to_numeric(
                        df_resumo[col_num], errors="coerce"
                    ).fillna(0)

            df_fardos = df_resumo[
                df_resumo["tipo_fardo"].astype(str).str.lower().isin(
                    ["fardinho", "fardao"]
                )
            ]
            df_perdas = df_resumo[
                df_resumo["tipo_fardo"].astype(str).str.lower() == "perdas"
            ]

            total_fardos_qtd = int(df_fardos["quantidade"].sum()) if not df_fardos.empty else 0
            total_fardos_peso = float(df_fardos["peso_kg"].sum()) if not df_fardos.empty else 0.0
            total_perdas_peso = float(df_perdas["perda_total_kg"].sum()) if not df_perdas.empty else 0.0
            n_fardinhos = len(df_fardos[df_fardos["tipo_fardo"].astype(str).str.lower() == "fardinho"]) if not df_fardos.empty else 0
            n_fardoes = len(df_fardos[df_fardos["tipo_fardo"].astype(str).str.lower() == "fardao"]) if not df_fardos.empty else 0

            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1:
                st.metric("Producao (fardos)", f"{total_fardos_qtd} un")
            with col_r2:
                st.metric("Peso Producao", formatar_peso(total_fardos_peso))
            with col_r3:
                st.metric("Perdas", formatar_peso(total_perdas_peso))
            with col_r4:
                st.metric("Fardinhos / Fardoes", f"{n_fardinhos} / {n_fardoes}")

            # Botao PDF
            if gerar_pdf_producao_lavacao is not None:
                try:
                    pdf_bytes = gerar_pdf_producao_lavacao(
                        data_str, turno, registros_turno, paradas_turno
                    )
                    st.download_button(
                        "Baixar PDF do Turno",
                        pdf_bytes,
                        file_name=f"producao_lavacao_{data_str}_{turno}.pdf",
                        mime="application/pdf",
                        key="pdf_turno",
                    )
                except Exception:
                    st.warning("Erro ao gerar PDF do turno.")
            else:
                st.info("Gerador de PDF nao disponivel.")
        else:
            st.info(
                f"Nenhum registro encontrado para {formatar_data(data_prod)} - "
                f"Turno {turno}."
            )


# ===========================================================================
# TAB: Paradas
# ===========================================================================
with tab_paradas:
    st.subheader("Registro de Paradas")

    with st.form("form_parada", clear_on_submit=True):
        col_par1, col_par2 = st.columns(2)
        with col_par1:
            data_parada = st.date_input(
                "Data", value=date.today(), key="data_parada"
            )
            if turno_fixo:
                turno_parada = turno_fixo
                st.info(f"Turno: **{turno_parada}**")
            else:
                turno_parada = st.selectbox(
                    "Turno", options=TURNOS, key="turno_parada"
                )
            tipo_parada = st.selectbox(
                "Tipo de Parada", options=TIPOS_PARADA, key="tipo_parada"
            )
        with col_par2:
            hora_inicio = st.time_input(
                "Hora Inicio", value=time(8, 0), key="hora_inicio_parada"
            )
            hora_fim = st.time_input(
                "Hora Fim", value=time(8, 30), key="hora_fim_parada"
            )
            observacao_parada = st.text_area(
                "Observacao", key="obs_parada"
            )

        submit_parada = st.form_submit_button(
            "Registrar Parada", type="primary", use_container_width=True
        )

    if submit_parada:
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
                st.success(
                    f"Parada registrada: **{tipo_parada}** - "
                    f"Duracao: {duracao_min} minutos"
                )
                st.rerun()
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
            df_paradas_exib = df_paradas.copy()
            df_paradas_exib["data"] = df_paradas_exib["data"].apply(formatar_data)
            colunas_parada = [
                "data", "turno", "tipo_parada", "hora_inicio",
                "hora_fim", "duracao_min", "observacao",
            ]
            colunas_presentes = [
                c for c in colunas_parada if c in df_paradas_exib.columns
            ]
            st.dataframe(
                df_paradas_exib[colunas_presentes],
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
        df_hist["data_dt"] = pd.to_datetime(
            df_hist["data"], errors="coerce"
        ).dt.date
        mask = (df_hist["data_dt"] >= hist_data_inicio) & (
            df_hist["data_dt"] <= hist_data_fim
        )
        df_filtrado = df_hist[mask].copy()

        # Filtrar por turno
        if hist_turno != "Todos":
            df_filtrado = df_filtrado[df_filtrado["turno"] == hist_turno]

        if df_filtrado.empty:
            st.info("Nenhum registro encontrado para os filtros selecionados.")
        else:
            # Converter colunas numericas
            for col_num in (
                "quantidade", "peso_kg", "perda_lixo_kg",
                "perda_papelao_kg", "perda_plastico_colorido_kg",
                "perda_total_kg",
            ):
                if col_num in df_filtrado.columns:
                    df_filtrado[col_num] = pd.to_numeric(
                        df_filtrado[col_num], errors="coerce"
                    ).fillna(0)

            # Separar fardos e perdas
            df_fardos_hist = df_filtrado[
                df_filtrado["tipo_fardo"]
                .astype(str)
                .str.lower()
                .isin(["fardinho", "fardao"])
            ]
            df_perdas_hist = df_filtrado[
                df_filtrado["tipo_fardo"].astype(str).str.lower() == "perdas"
            ]

            total_registros = len(df_fardos_hist)
            total_peso = float(df_fardos_hist["peso_kg"].sum()) if not df_fardos_hist.empty else 0.0
            total_perdas = float(df_perdas_hist["perda_total_kg"].sum()) if not df_perdas_hist.empty else 0.0
            total_fardinhos = len(
                df_fardos_hist[
                    df_fardos_hist["tipo_fardo"].astype(str).str.lower()
                    == "fardinho"
                ]
            )
            total_fardoes = len(
                df_fardos_hist[
                    df_fardos_hist["tipo_fardo"].astype(str).str.lower()
                    == "fardao"
                ]
            )

            # Metricas resumo
            col_m1, col_m2, col_m3, col_m4 = st.columns(4)
            with col_m1:
                st.metric("Total Registros", total_registros)
            with col_m2:
                st.metric("Peso Total Fardos", formatar_peso(total_peso))
            with col_m3:
                st.metric("Perdas Total", formatar_peso(total_perdas))
            with col_m4:
                st.metric(
                    "Fardinhos / Fardoes",
                    f"{total_fardinhos} / {total_fardoes}",
                )

            st.divider()

            # Tabela de dados
            colunas_exibir = [
                "data", "turno", "numero_op", "tipo_fardo", "nf",
                "quantidade", "peso_kg", "perda_lixo_kg", "perda_papelao_kg",
                "perda_plastico_colorido_kg", "perda_total_kg",
                "registrado_por",
            ]
            colunas_presentes = [
                c for c in colunas_exibir if c in df_filtrado.columns
            ]
            df_exibir = df_filtrado[colunas_presentes].copy()
            df_exibir["data"] = df_exibir["data"].apply(formatar_data)

            st.dataframe(
                df_exibir, use_container_width=True, hide_index=True
            )
