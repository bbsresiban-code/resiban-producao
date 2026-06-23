import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, time, datetime

from utils.database import read_sheet, read_sheet_no_cache, append_row, update_row_multi
from utils.serial_code import gerar_codigo_serial, preview_codigo
from utils.formatters import (
    TURNOS,
    EXTRUSORAS,
    TIPOS_PRODUTO,
    formatar_peso,
    formatar_data,
    formatar_duracao,
)

try:
    from utils.pdf_generator import gerar_pdf_producao_extrusao
except ImportError:
    gerar_pdf_producao_extrusao = None

st.title("Producao Extrusao")

usuario_logado = st.session_state.get("usuario", "master")
perfil_logado = st.session_state.get("perfil", "master")
if perfil_logado == "turno":
    turno_fixo_ext = usuario_logado[-1].upper()
else:
    turno_fixo_ext = None


def carregar_registro_turno_ext(data_str: str, turno: str):
    """Retorna a linha de turno_extrusao (dict) para data+turno, ou None."""
    try:
        df = read_sheet_no_cache("turno_extrusao")
        if df.empty:
            return None
        m = (df["data"].astype(str) == data_str) & (df["turno"].astype(str) == turno)
        sub = df[m]
        return sub.iloc[0].to_dict() if not sub.empty else None
    except Exception:
        return None


def duracao_minutos_ext(hora_inicio: str, hora_fim: str):
    """Minutos entre 'HH:MM' (assume virada de meia-noite se fim<=inicio)."""
    try:
        hi = datetime.strptime(str(hora_inicio), "%H:%M")
        hf = datetime.strptime(str(hora_fim), "%H:%M")
    except (ValueError, TypeError):
        return None
    delta = (hf - hi).total_seconds() / 60
    if delta <= 0:
        delta += 24 * 60
    return int(delta)


tab_lote, tab_manut, tab_hist = st.tabs(["Novo Lote", "Manutencao", "Historico"])

# ---------------------------------------------------------------------------
# Tab: Novo Lote
# ---------------------------------------------------------------------------
with tab_lote:
    st.subheader("Registrar Novo Lote de Extrusao")

    try:
        df_ops = read_sheet("op_extrusao")
    except Exception as exc:
        st.error(f"Erro ao carregar OPs: {exc}")
        df_ops = pd.DataFrame()

    ops_abertas = []
    if not df_ops.empty and "status" in df_ops.columns:
        ops_abertas = df_ops[df_ops["status"] == "aberta"]["numero_op"].tolist()

    if not ops_abertas:
        st.warning("Nenhuma OP de extrusao aberta. Crie uma OP antes de registrar lotes.")
    else:
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            data_lote = st.date_input("Data", value=date.today(), key="lote_data")
        with col_s2:
            if turno_fixo_ext:
                turno = turno_fixo_ext
                st.info(f"Turno: **{turno}**")
            else:
                turno = st.selectbox("Turno", options=TURNOS, key="lote_turno")
        with col_s3:
            numero_op = st.selectbox("Numero da OP", options=ops_abertas, key="lote_op")

        # Banner do ultimo lote registrado (persiste apos o rerun de limpeza)
        if st.session_state.get("lote_ultimo_codigo"):
            st.success(f"Ultimo lote registrado: **{st.session_state['lote_ultimo_codigo']}**")

        # Buscar dados da OP selecionada
        tipo = "01"
        origem_op = "Proprio"
        opl_origem = ""
        extrusora = EXTRUSORAS[0]
        aditivo_pct_ope = 0.0
        volume_ton_ope = 0.0
        try:
            op_sel_row = df_ops[df_ops["numero_op"] == numero_op].iloc[0]
            tipo_op = str(op_sel_row.get("tipo_lote", "")).strip()
            if tipo_op in ("01", "02"):
                tipo = tipo_op
            origem_op = str(op_sel_row.get("origem", "Proprio"))
            opl_origem = str(op_sel_row.get("opl_origem", ""))
            extrusora = str(op_sel_row.get("maquina", "") or "").strip() or EXTRUSORAS[0]
            aditivo_pct_ope = float(op_sel_row.get("aditivo_percentual", 0) or 0)
            volume_ton_ope = float(op_sel_row.get("volume_ton", 0) or 0)
        except Exception:
            pass

        tipo_desc = TIPOS_PRODUTO.get(tipo, "Produto Proprio")
        ope_tem_aditivo = aditivo_pct_ope > 0

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            info_origem = f"Origem: **{origem_op}** (Lote tipo **{tipo}** - {tipo_desc})"
            if opl_origem:
                info_origem += f"  \nOPL de origem: **{opl_origem}**"
            st.info(info_origem)
        with col_t2:
            # Item 4: extrusora vem da OPE, sem escolha no lancamento
            st.info(f"Extrusora: **{extrusora}** (definida na OPE)")

        # -------------------------------------------------------------------
        # Item 5: Controle de Turno (inicio / fim)
        # -------------------------------------------------------------------
        with st.container(border=True):
            st.markdown("#### Controle de Turno")
            reg_turno = carregar_registro_turno_ext(data_lote.isoformat(), turno)
            h_ini = str(reg_turno.get("hora_inicio", "") or "") if reg_turno else ""
            h_fim = str(reg_turno.get("hora_fim", "") or "") if reg_turno else ""
            col_ct1, col_ct2 = st.columns([2, 1])
            with col_ct1:
                if not reg_turno or not h_ini:
                    st.caption(f"Turno {turno} - {formatar_data(data_lote)}: **nao iniciado**.")
                elif not h_fim:
                    st.success(f"Turno {turno} iniciado as **{h_ini}** (em andamento).")
                else:
                    dur = duracao_minutos_ext(h_ini, h_fim)
                    st.info(f"Turno {turno}: **{h_ini} -> {h_fim}** (duracao {formatar_duracao(dur) if dur is not None else '-'})")
            with col_ct2:
                agora = datetime.now().strftime("%H:%M")
                if not reg_turno or not h_ini:
                    if st.button("Iniciar Turno", type="primary", use_container_width=True, key="btn_iniciar_turno_ext"):
                        try:
                            append_row("turno_extrusao", {
                                "data": data_lote.isoformat(), "turno": turno,
                                "numero_op": numero_op, "hora_inicio": agora, "hora_fim": "",
                                "registrado_por": usuario_logado, "observacao": "",
                            })
                            st.toast(f"Turno iniciado as {agora}")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erro ao iniciar turno: {exc}")
                elif not h_fim:
                    if st.button("Encerrar Turno", type="primary", use_container_width=True, key="btn_encerrar_turno_ext"):
                        try:
                            update_row_multi("turno_extrusao", "id", str(reg_turno["id"]), {"hora_fim": agora})
                            st.toast(f"Turno encerrado as {agora}")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erro ao encerrar turno: {exc}")
            if reg_turno:
                with st.expander("Ajustar horarios"):
                    with st.form("form_ajustar_turno_ext", clear_on_submit=False):
                        try:
                            v_ini = datetime.strptime(h_ini, "%H:%M").time() if h_ini else time(6, 0)
                        except ValueError:
                            v_ini = time(6, 0)
                        try:
                            v_fim = datetime.strptime(h_fim, "%H:%M").time() if h_fim else time(14, 0)
                        except ValueError:
                            v_fim = time(14, 0)
                        col_aj1, col_aj2 = st.columns(2)
                        with col_aj1:
                            aj_ini = st.time_input("Hora Inicio", value=v_ini, key="aj_ini_turno_ext")
                        with col_aj2:
                            aj_fim = st.time_input("Hora Fim", value=v_fim, key="aj_fim_turno_ext")
                        if st.form_submit_button("Salvar horarios", use_container_width=True):
                            try:
                                update_row_multi("turno_extrusao", "id", str(reg_turno["id"]), {
                                    "hora_inicio": aj_ini.strftime("%H:%M"),
                                    "hora_fim": aj_fim.strftime("%H:%M"),
                                })
                                st.toast("Horarios atualizados!")
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Erro ao salvar horarios: {exc}")

        # -------------------------------------------------------------------
        # Item 8: limite de volume da OPE (+850 kg de folga)
        # -------------------------------------------------------------------
        try:
            df_extra_ope = read_sheet("ope_material_extra")
            extras_kg = 0.0
            if not df_extra_ope.empty and "numero_op" in df_extra_ope.columns:
                sel_x = df_extra_ope[df_extra_ope["numero_op"].astype(str) == str(numero_op)]
                extras_kg = float(pd.to_numeric(sel_x.get("peso_kg", 0), errors="coerce").fillna(0).sum())
        except Exception:
            extras_kg = 0.0

        try:
            df_prod_ope = read_sheet("producao_extrusao")
            produzido_kg = 0.0
            if not df_prod_ope.empty and "numero_op" in df_prod_ope.columns:
                sel_p = df_prod_ope[df_prod_ope["numero_op"].astype(str) == str(numero_op)]
                produzido_kg = float(pd.to_numeric(sel_p.get("peso_kg", 0), errors="coerce").fillna(0).sum())
        except Exception:
            produzido_kg = 0.0

        FOLGA_KG = 850.0
        volume_previsto_kg = volume_ton_ope * 1000 + extras_kg
        limite_kg = volume_previsto_kg + FOLGA_KG
        restante_kg = limite_kg - produzido_kg

        col_v1, col_v2, col_v3 = st.columns(3)
        col_v1.metric("Previsto (+extra)", formatar_peso(volume_previsto_kg))
        col_v2.metric("Produzido", formatar_peso(produzido_kg))
        col_v3.metric("Restante (c/ folga 850)", formatar_peso(max(0.0, restante_kg)))

        pode_lancar = restante_kg > 0
        if not pode_lancar:
            st.error(
                f"OPE {numero_op} atingiu o limite de producao "
                f"({formatar_peso(limite_kg)} = previsto + 850 kg). Nao e possivel lancar mais lotes."
            )

        if pode_lancar:
            # --- Serial code preview ---
            codigo_preview = preview_codigo(tipo, extrusora, data_lote)
            st.info(f"Codigo do lote (preview): **{codigo_preview}**")

            # --- Dados do lote ---
            st.markdown("---")
            col_f1, col_f2 = st.columns(2)
            with col_f1:
                peso_kg = st.number_input(
                    "Peso (kg)", min_value=0.0, max_value=float(restante_kg),
                    step=0.5, format="%.1f", key="lote_peso", value=None,
                    help=f"Maximo permitido agora: {formatar_peso(restante_kg)}",
                )
                hora = st.time_input("Hora", value=datetime.now().time(), key="lote_hora")
                if ope_tem_aditivo:
                    aditivo_gramas = st.number_input(
                        "Aditivo (gramas)", min_value=0.0, step=10.0, value=None, format="%.1f",
                        key="lote_aditivo_g",
                        help=f"OPE preve {aditivo_pct_ope:.2f}% de aditivo",
                    )
                else:
                    aditivo_gramas = 0
                    st.caption("OPE sem aditivo previsto - aditivo bloqueado.")
            with col_f2:
                observacao_lote = st.text_input("Observacao", key="lote_obs")
                registrado_por = st.text_input(
                    "Registrado por *", value=usuario_logado, key="lote_reg"
                )
                if peso_kg and peso_kg > 0:
                    perc_reciclado_lote = ((peso_kg * 1000 - (aditivo_gramas or 0)) / (peso_kg * 1000)) * 100
                    st.metric("Conteudo Reciclado", f"{perc_reciclado_lote:.2f}%")
                else:
                    perc_reciclado_lote = 0.0

            # --- Troca de telas (condicional por extrusora) ---
            qtd_troca_telas = 0
            qtd_1o_estagio = 0
            qtd_2o_estagio = 0
            troca_telas = "Nao"

            if extrusora == "A":
                st.markdown("**Troca de Telas** *(obrigatorio para Extrusora A)*")
                col_tt1, col_tt2 = st.columns(2)
                with col_tt1:
                    qtd_1o_estagio = st.number_input(
                        "Telas 1o Estagio", min_value=0, step=1, value=None,
                        key="lote_telas_1e",
                    )
                with col_tt2:
                    qtd_2o_estagio = st.number_input(
                        "Telas 2o Estagio", min_value=0, step=1, value=None,
                        key="lote_telas_2e",
                    )
                qtd_troca_telas = (qtd_1o_estagio or 0) + (qtd_2o_estagio or 0)
                troca_telas = "Sim"
            else:
                col_tt1, col_tt2 = st.columns(2)
                with col_tt1:
                    troca_telas = st.selectbox(
                        "Troca de Telas",
                        options=["Nao", "Sim"],
                        key="lote_troca_telas",
                    )
                with col_tt2:
                    if troca_telas == "Sim":
                        qtd_troca_telas = st.number_input(
                            "Quantas telas?", min_value=1, step=1, value=None,
                            key="lote_qtd_telas",
                        )

            submitted = st.button("Registrar Lote", type="primary", use_container_width=True)

            if submitted:
                erros = []
                if not peso_kg or peso_kg <= 0:
                    erros.append("Peso deve ser maior que zero.")
                elif peso_kg > restante_kg:
                    erros.append(f"Peso acima do limite restante ({formatar_peso(restante_kg)}).")
                if not registrado_por.strip():
                    erros.append("Campo 'Registrado por' e obrigatorio.")
                if extrusora == "A" and (qtd_troca_telas or 0) == 0:
                    erros.append("Extrusora A: informe a quantidade de telas trocadas (1o e/ou 2o estagio).")

                if erros:
                    for e in erros:
                        st.error(e)
                else:
                    try:
                        codigo_lote, sequencial = gerar_codigo_serial(
                            tipo, extrusora, data_lote
                        )

                        dados = {
                            "data": data_lote.isoformat(),
                            "turno": turno,
                            "hora": hora.strftime("%H:%M"),
                            "numero_op": numero_op,
                            "opl_origem": opl_origem,
                            "codigo_lote": codigo_lote,
                            "tipo": tipo,
                            "tipo_descricao": TIPOS_PRODUTO[tipo],
                            "extrusora": extrusora,
                            "peso_kg": float(peso_kg or 0),
                            "aditivo_gramas": float(aditivo_gramas or 0),
                            "perc_reciclado": round(perc_reciclado_lote, 2),
                            "troca_telas": f"Sim (1E:{int(qtd_1o_estagio or 0)} 2E:{int(qtd_2o_estagio or 0)})" if extrusora == "A" else (f"Sim ({int(qtd_troca_telas or 0)})" if troca_telas == "Sim" else "Nao"),
                            "mes": data_lote.month,
                            "ano": data_lote.year % 100,
                            "sequencial": sequencial,
                            "status": "em_analise",
                            "observacao_lote": observacao_lote.strip(),
                            "registrado_por": registrado_por.strip(),
                        }

                        append_row("producao_extrusao", dados)
                        # Item 2: limpar campos de lancamento e recarregar
                        st.session_state["lote_ultimo_codigo"] = codigo_lote
                        for k in ["lote_peso", "lote_hora", "lote_aditivo_g", "lote_obs",
                                  "lote_reg", "lote_telas_1e", "lote_telas_2e",
                                  "lote_troca_telas", "lote_qtd_telas"]:
                            st.session_state.pop(k, None)
                        st.toast(f"Lote {codigo_lote} registrado!")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro ao registrar lote: {exc}")

        # ---------------------------------------------------------------
        # Relatorio do Turno (PDF consolidado)
        # ---------------------------------------------------------------
        st.divider()
        st.subheader("Relatorio do Turno")

        data_str_turno = data_lote.isoformat()
        try:
            df_turno_ext = read_sheet("producao_extrusao")
            df_manut_turno = read_sheet("manutencao_extrusao")
        except Exception:
            df_turno_ext = pd.DataFrame()
            df_manut_turno = pd.DataFrame()

        registros_turno = []
        if not df_turno_ext.empty:
            mask_t = (
                (df_turno_ext["data"].astype(str) == data_str_turno)
                & (df_turno_ext["turno"].astype(str) == turno)
            )
            df_turno_f = df_turno_ext[mask_t]
            if not df_turno_f.empty:
                registros_turno = df_turno_f.to_dict("records")

        manutencao_turno = []
        if not df_manut_turno.empty:
            mask_m = (
                (df_manut_turno["data"].astype(str) == data_str_turno)
                & (df_manut_turno["turno"].astype(str) == turno)
            )
            df_manut_f = df_manut_turno[mask_m]
            if not df_manut_f.empty:
                manutencao_turno = df_manut_f.to_dict("records")

        if registros_turno:
            total_lotes_t = len(registros_turno)
            total_kg_t = sum(float(r.get("peso_kg", 0) or 0) for r in registros_turno)
            trocas_total = 0
            for r in registros_turno:
                tt = str(r.get("troca_telas", ""))
                if tt.startswith("Sim"):
                    try:
                        qtd = int(tt.split("(")[1].replace(")", ""))
                        trocas_total += qtd
                    except (IndexError, ValueError):
                        trocas_total += 1
            trocas_sim = trocas_total
            col_rt1, col_rt2, col_rt3 = st.columns(3)
            col_rt1.metric("Lotes no Turno", total_lotes_t)
            col_rt2.metric("Peso Total", formatar_peso(total_kg_t))
            col_rt3.metric("Trocas de Tela", trocas_sim)

            # Eficiencia do turno (usa inicio/fim do turno_extrusao)
            reg_t = carregar_registro_turno_ext(data_str_turno, turno)
            h_ini_t = str(reg_t.get("hora_inicio", "") or "") if reg_t else ""
            h_fim_t = str(reg_t.get("hora_fim", "") or "") if reg_t else ""
            dur_turno = None
            kg_h = None
            if h_ini_t and h_fim_t:
                dur_turno = duracao_minutos_ext(h_ini_t, h_fim_t)
                if dur_turno and dur_turno > 0:
                    kg_h = total_kg_t / (dur_turno / 60)

            st.markdown("##### Eficiencia do Turno")
            if dur_turno is None:
                st.info("Registre o inicio e o fim do turno (secao 'Controle de Turno') para calcular a eficiencia.")
            else:
                col_e1, col_e2 = st.columns(2)
                col_e1.metric("Duracao Turno", formatar_duracao(dur_turno))
                col_e2.metric("Produtividade", f"{(kg_h or 0):,.0f} kg/h".replace(",", "."))

            turno_info = {
                "hora_inicio": h_ini_t, "hora_fim": h_fim_t,
                "duracao_bruta": dur_turno, "kg_h": kg_h,
            }

            if gerar_pdf_producao_extrusao is not None:
                try:
                    pdf_bytes = gerar_pdf_producao_extrusao(
                        data_str_turno, turno, registros_turno, manutencao_turno, turno_info
                    )
                    st.download_button(
                        "Baixar PDF do Turno",
                        pdf_bytes,
                        file_name=f"extrusao_{data_str_turno}_{turno}.pdf",
                        mime="application/pdf",
                        type="primary",
                        use_container_width=True,
                    )
                except Exception:
                    pass
        else:
            st.info("Nenhum lote registrado neste turno ainda.")

# ---------------------------------------------------------------------------
# Tab: Manutencao
# ---------------------------------------------------------------------------
with tab_manut:
    st.subheader("Registro de Manutencao - Extrusao")
    st.caption("Troca de telas e registrada junto ao lote na aba 'Novo Lote'.")

    with st.form("form_manutencao_extrusao", clear_on_submit=True):
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            data_manut = st.date_input("Data", value=date.today(), key="manut_data")
            if turno_fixo_ext:
                turno_manut = turno_fixo_ext
                st.info(f"Turno: **{turno_manut}**")
            else:
                turno_manut = st.selectbox("Turno", options=TURNOS, key="manut_turno")
        with col_m2:
            limpeza_gaveta = st.text_input("Limpeza de Gaveta")
            troca_facas = st.text_input("Troca de Facas")

        observacao_manut = st.text_area("Observacao")

        submitted_manut = st.form_submit_button(
            "Registrar Manutencao", use_container_width=True
        )

        if submitted_manut:
            try:
                dados_manut = {
                    "data": data_manut.isoformat(),
                    "turno": turno_manut,
                    "troca_telas": "",
                    "limpeza_gaveta": limpeza_gaveta.strip(),
                    "troca_facas": troca_facas.strip(),
                    "observacao": observacao_manut.strip(),
                }
                append_row("manutencao_extrusao", dados_manut)
                st.success("Manutencao registrada com sucesso!")
            except Exception as exc:
                st.error(f"Erro ao registrar manutencao: {exc}")

# ---------------------------------------------------------------------------
# Tab: Historico
# ---------------------------------------------------------------------------
with tab_hist:
    st.subheader("Historico de Producao - Extrusao")

    # Filters
    col_h1, col_h2, col_h3 = st.columns(3)
    with col_h1:
        hist_inicio = st.date_input(
            "Data Inicio",
            value=date.today().replace(day=1),
            key="hist_ini",
        )
        hist_fim = st.date_input("Data Fim", value=date.today(), key="hist_fim")
    with col_h2:
        hist_turno = st.multiselect("Turno", options=TURNOS, default=TURNOS, key="hist_turno")
    with col_h3:
        hist_extrusora = st.multiselect(
            "Extrusora", options=EXTRUSORAS, default=EXTRUSORAS, key="hist_ext"
        )

    try:
        df_hist = read_sheet("producao_extrusao")
    except Exception as exc:
        st.error(f"Erro ao carregar historico: {exc}")
        df_hist = pd.DataFrame()

    if not df_hist.empty:
        df_hist["data_dt"] = pd.to_datetime(df_hist["data"], errors="coerce")
        mask = (
            (df_hist["data_dt"] >= pd.Timestamp(hist_inicio))
            & (df_hist["data_dt"] <= pd.Timestamp(hist_fim))
        )
        if hist_turno:
            mask = mask & (df_hist["turno"].isin(hist_turno))
        if hist_extrusora:
            mask = mask & (df_hist["extrusora"].isin(hist_extrusora))

        df_filtrado = df_hist[mask].copy()

        if df_filtrado.empty:
            st.info("Nenhum lote encontrado para os filtros selecionados.")
        else:
            # Color-code status
            def cor_status(val):
                cores = {
                    "em_analise": "background-color: #fff3cd; color: #856404",
                    "disponivel": "background-color: #d4edda; color: #155724",
                    "carregado": "background-color: #e2e3e5; color: #383d41",
                }
                return cores.get(val, "")

            colunas_exibir = [
                c for c in [
                    "codigo_lote", "data", "turno", "numero_op", "extrusora",
                    "tipo_descricao", "peso_kg", "troca_telas", "status",
                    "registrado_por",
                ] if c in df_filtrado.columns
            ]

            styled_df = df_filtrado[colunas_exibir].sort_values(
                "data", ascending=False
            )

            if "status" in styled_df.columns:
                st.dataframe(
                    styled_df.style.map(cor_status, subset=["status"]),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                st.dataframe(
                    styled_df,
                    use_container_width=True,
                    hide_index=True,
                )

            # Summary metrics
            st.markdown("---")
            st.subheader("Resumo do Periodo")

            df_filtrado["peso_kg_num"] = pd.to_numeric(
                df_filtrado["peso_kg"], errors="coerce"
            )

            total_lotes = len(df_filtrado)
            total_kg = df_filtrado["peso_kg_num"].sum()

            col_met1, col_met2 = st.columns(2)
            with col_met1:
                st.metric("Total de Lotes", total_lotes)
            with col_met2:
                st.metric("Total Produzido", formatar_peso(total_kg))

            # By extruder
            if "extrusora" in df_filtrado.columns:
                st.markdown("**Producao por Extrusora:**")
                resumo_ext = (
                    df_filtrado.groupby("extrusora")
                    .agg(
                        lotes=("extrusora", "count"),
                        peso_total=("peso_kg_num", "sum"),
                    )
                    .reset_index()
                )
                resumo_ext["peso_total"] = resumo_ext["peso_total"].apply(formatar_peso)
                resumo_ext.columns = ["Extrusora", "Lotes", "Peso Total"]
                st.dataframe(resumo_ext, use_container_width=True, hide_index=True)
    else:
        st.info("Nenhum dado de producao encontrado.")
