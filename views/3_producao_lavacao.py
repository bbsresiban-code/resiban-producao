import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta, time

from utils.database import (
    read_sheet, read_sheet_no_cache, append_row, update_row_multi,
)
from utils.formatters import (
    formatar_data, formatar_peso, formatar_duracao, TURNOS, TIPOS_PARADA,
    fardos_breakdown, tipo_fardo_label, formatar_fardos,
)

try:
    from utils.pdf_generator import gerar_pdf_producao_lavacao
except ImportError:
    gerar_pdf_producao_lavacao = None

# ---------------------------------------------------------------------------
# Titulo
# ---------------------------------------------------------------------------
st.header("Producao - Lavacao")

# ---------------------------------------------------------------------------
# Perfil / turno do usuario logado (usado por todas as abas)
# ---------------------------------------------------------------------------
usuario_logado = st.session_state.get("usuario", "master")
perfil_logado = st.session_state.get("perfil", "master")
if perfil_logado == "turno":
    turno_fixo = usuario_logado[-1].upper()
else:
    turno_fixo = None

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
            fa, fi = fardos_breakdown(row)
            resultado.append({
                "nf_apara": str(row.get("nf_apara", "")),
                "fornecedor": str(row.get("fornecedor", "")),
                "tipo_fardo": tipo_fardo_label(fa, fi) or "Fardinho",
                "qtd_fardao": fa,
                "qtd_fardinho": fi,
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


def carregar_registro_turno(data_str: str, turno: str) -> dict | None:
    """Retorna a linha de turno_lavacao (dict) para data+turno, ou None."""
    try:
        df = read_sheet_no_cache("turno_lavacao")
        if df.empty:
            return None
        m = (df["data"].astype(str) == data_str) & (df["turno"].astype(str) == turno)
        sub = df[m]
        if sub.empty:
            return None
        return sub.iloc[0].to_dict()
    except Exception:
        return None


def duracao_minutos(hora_inicio: str, hora_fim: str) -> int | None:
    """Minutos entre 'HH:MM' inicio e fim (assume virada de meia-noite se fim<=inicio)."""
    try:
        hi = datetime.strptime(str(hora_inicio), "%H:%M")
        hf = datetime.strptime(str(hora_fim), "%H:%M")
    except (ValueError, TypeError):
        return None
    delta = (hf - hi).total_seconds() / 60
    if delta <= 0:
        delta += 24 * 60
    return int(delta)


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

    data_str_sel = data_prod.isoformat()

    # -------------------------------------------------------------------
    # Secao: Controle de Turno (inicio / fim)
    # -------------------------------------------------------------------
    st.divider()
    with st.container(border=True):
        st.markdown("#### Controle de Turno")
        reg_turno = carregar_registro_turno(data_str_sel, turno)
        h_ini = str(reg_turno.get("hora_inicio", "") or "") if reg_turno else ""
        h_fim = str(reg_turno.get("hora_fim", "") or "") if reg_turno else ""

        col_ct1, col_ct2 = st.columns([2, 1])
        with col_ct1:
            if not reg_turno or not h_ini:
                st.caption(f"Turno {turno} - {formatar_data(data_prod)}: **nao iniciado**.")
            elif not h_fim:
                st.success(f"Turno {turno} iniciado as **{h_ini}** (em andamento).")
            else:
                dur = duracao_minutos(h_ini, h_fim)
                st.info(
                    f"Turno {turno}: **{h_ini} -> {h_fim}** "
                    f"(duracao {formatar_duracao(dur) if dur is not None else '-'})"
                )
        with col_ct2:
            agora = datetime.now().strftime("%H:%M")
            if not reg_turno or not h_ini:
                if st.button("Iniciar Turno", type="primary", use_container_width=True, key="btn_iniciar_turno"):
                    try:
                        append_row("turno_lavacao", {
                            "data": data_str_sel,
                            "turno": turno,
                            "numero_op": numero_op or "",
                            "hora_inicio": agora,
                            "hora_fim": "",
                            "registrado_por": usuario_logado,
                            "observacao": "",
                        })
                        st.toast(f"Turno iniciado as {agora}")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro ao iniciar turno: {exc}")
            elif not h_fim:
                if st.button("Encerrar Turno", type="primary", use_container_width=True, key="btn_encerrar_turno"):
                    try:
                        update_row_multi("turno_lavacao", "id", str(reg_turno["id"]), {"hora_fim": agora})
                        st.toast(f"Turno encerrado as {agora}")
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro ao encerrar turno: {exc}")

        # Ajuste manual dos horarios (correcao)
        if reg_turno:
            with st.expander("Ajustar horarios"):
                with st.form("form_ajustar_turno", clear_on_submit=False):
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
                        aj_ini = st.time_input("Hora Inicio", value=v_ini, key="aj_ini_turno")
                    with col_aj2:
                        aj_fim = st.time_input("Hora Fim", value=v_fim, key="aj_fim_turno")
                    if st.form_submit_button("Salvar horarios", use_container_width=True):
                        try:
                            update_row_multi("turno_lavacao", "id", str(reg_turno["id"]), {
                                "hora_inicio": aj_ini.strftime("%H:%M"),
                                "hora_fim": aj_fim.strftime("%H:%M"),
                            })
                            st.toast("Horarios atualizados!")
                            st.rerun()
                        except Exception as exc:
                            st.error(f"Erro ao salvar horarios: {exc}")

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
    # Calcular planejado/lancado/restante por NF
    # -------------------------------------------------------------------
    def _cor_progresso(val):
        if val >= 100:
            return "background-color: #d4edda; color: #155724"
        elif val > 0:
            return "background-color: #fff3cd; color: #856404"
        return "background-color: #f8d7da; color: #721c24"

    nf_calc = []
    if numero_op and nfs_da_op:
        for idx_nf, nf_info in enumerate(nfs_da_op):
            nf_numero = nf_info["nf_apara"]
            nf_fa_plan = int(nf_info.get("qtd_fardao", 0) or 0)
            nf_fi_plan = int(nf_info.get("qtd_fardinho", 0) or 0)
            nf_peso_plan = float(nf_info["peso_kg"])

            fa_lancado = 0
            fi_lancado = 0
            peso_lancado = 0.0
            if not df_prod_existente.empty:
                mask_nf = df_prod_existente["nf"].astype(str) == nf_numero
                if mask_nf.any():
                    sub_nf = df_prod_existente.loc[mask_nf]
                    for _, pr in sub_nf.iterrows():
                        pfa, pfi = fardos_breakdown(pr)
                        fa_lancado += pfa
                        fi_lancado += pfi
                    peso_lancado = float(sub_nf["peso_kg"].sum())

            fa_rest = max(0, nf_fa_plan - fa_lancado)
            fi_rest = max(0, nf_fi_plan - fi_lancado)
            peso_rest = max(0.0, nf_peso_plan - peso_lancado)
            pct = (peso_lancado / nf_peso_plan * 100) if nf_peso_plan > 0 else 0.0

            nf_calc.append({
                "idx": idx_nf, "info": nf_info,
                "fa_plan": nf_fa_plan, "fi_plan": nf_fi_plan, "peso_plan": nf_peso_plan,
                "fa_lanc": fa_lancado, "fi_lanc": fi_lancado, "peso_lanc": peso_lancado,
                "fa_rest": fa_rest, "fi_rest": fi_rest, "peso_rest": peso_rest,
                "pct": round(pct, 1),
            })

    # -------------------------------------------------------------------
    # Resumo geral (todas as NFs da OP)
    # -------------------------------------------------------------------
    if nf_calc:
        st.subheader("Progresso da OP")
        linhas_resumo = []
        for c in nf_calc:
            info = c["info"]
            linhas_resumo.append({
                "NF": info["nf_apara"],
                "Fornecedor": info["fornecedor"],
                "Planejado": formatar_fardos(c["fa_plan"], c["fi_plan"]),
                "Lancado": formatar_fardos(c["fa_lanc"], c["fi_lanc"]),
                "Restante": formatar_fardos(c["fa_rest"], c["fi_rest"]),
                "Peso Plan.": c["peso_plan"],
                "Peso Lanc.": c["peso_lanc"],
                "% Concl.": c["pct"],
            })
        df_resumo_nf = pd.DataFrame(linhas_resumo)
        styled_resumo = df_resumo_nf.style.map(_cor_progresso, subset=["% Concl."]).format(
            {"Peso Plan.": "{:.1f}", "Peso Lanc.": "{:.1f}", "% Concl.": "{:.1f}%"}
        )
        st.dataframe(styled_resumo, use_container_width=True, hide_index=True)

        tot_peso_plan = sum(c["peso_plan"] for c in nf_calc)
        tot_peso_lanc = sum(c["peso_lanc"] for c in nf_calc)
        pct_geral = (tot_peso_lanc / tot_peso_plan * 100) if tot_peso_plan > 0 else 0.0
        st.progress(min(pct_geral / 100, 1.0), text=f"OP {pct_geral:.1f}% concluida (por peso)")

    # -------------------------------------------------------------------
    # Secao: A Lancar (apenas NFs com restante)
    # -------------------------------------------------------------------
    pendentes = [c for c in nf_calc if (c["fa_rest"] + c["fi_rest"]) > 0 and c["peso_rest"] > 0]
    if nf_calc and not pendentes:
        st.success("Todas as NFs desta OP foram totalmente lancadas.")

    for c in pendentes:
        info = c["info"]
        idx_nf = c["idx"]
        nf_numero = info["nf_apara"]
        nf_tipo = info["tipo_fardo"]
        with st.container(border=True):
            st.markdown(f"**NF {nf_numero}** - {info['fornecedor']} ({nf_tipo})")
            st.progress(
                min(c["pct"] / 100, 1.0),
                text=(
                    f"{c['pct']:.0f}% | Restante: "
                    f"{formatar_fardos(c['fa_rest'], c['fi_rest'])} / {formatar_peso(c['peso_rest'])}"
                ),
            )
            with st.form(f"form_nf_{idx_nf}_{nf_numero}", clear_on_submit=True):
                col_f1, col_f2, col_f3, col_f4 = st.columns(4)
                with col_f1:
                    if c["fa_plan"] > 0:
                        reg_fa_in = st.number_input(
                            "Qtd Fardoes", min_value=0, max_value=c["fa_rest"],
                            step=1, key=f"fa_nf_{idx_nf}", value=None,
                        )
                    else:
                        reg_fa_in = None
                        st.caption("Sem fardoes")
                with col_f2:
                    if c["fi_plan"] > 0:
                        reg_fi_in = st.number_input(
                            "Qtd Fardinhos", min_value=0, max_value=c["fi_rest"],
                            step=1, key=f"fi_nf_{idx_nf}", value=None,
                        )
                    else:
                        reg_fi_in = None
                        st.caption("Sem fardinhos")
                with col_f3:
                    peso_kg = st.number_input(
                        "Peso (kg)", min_value=0.0, max_value=float(c["peso_rest"]),
                        step=0.5, format="%.1f", key=f"peso_nf_{idx_nf}", value=None,
                    )
                with col_f4:
                    hora_fardo = st.time_input(
                        "Hora", value=datetime.now().time(), key=f"hora_nf_{idx_nf}",
                    )
                submit_nf = st.form_submit_button(
                    "Registrar producao", type="primary", use_container_width=True,
                )

            if submit_nf:
                reg_fa = int(reg_fa_in or 0)
                reg_fi = int(reg_fi_in or 0)
                qtd_total = reg_fa + reg_fi
                erros = []
                if qtd_total <= 0:
                    erros.append("Informe a quantidade de fardoes e/ou fardinhos.")
                if not peso_kg or peso_kg <= 0:
                    erros.append("Peso deve ser maior que zero.")
                if erros:
                    for e in erros:
                        st.error(e)
                else:
                    try:
                        tipo_reg = tipo_fardo_label(reg_fa, reg_fi).lower() or nf_tipo.lower()
                        dados = {
                            "data": data_prod.isoformat(),
                            "turno": turno,
                            "hora": hora_fardo.strftime("%H:%M"),
                            "numero_op": numero_op,
                            "tipo_fardo": tipo_reg,
                            "qtd_fardao": reg_fa,
                            "qtd_fardinho": reg_fi,
                            "nf": nf_numero,
                            "quantidade": qtd_total,
                            "peso_kg": float(peso_kg or 0),
                            "perda_lixo_kg": 0,
                            "perda_papelao_kg": 0,
                            "perda_plastico_colorido_kg": 0,
                            "perda_total_kg": 0,
                            "registrado_por": usuario_logado,
                        }
                        append_row("producao_lavacao", dados)
                        st.toast("Producao registrada com sucesso!")
                        st.success(
                            f"NF **{nf_numero}** - {formatar_fardos(reg_fa, reg_fi)} / "
                            f"{formatar_peso(float(peso_kg or 0))} as {hora_fardo.strftime('%H:%M')}."
                        )
                        st.rerun()
                    except Exception as exc:
                        st.error(f"Erro ao registrar producao: {exc}")

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
                df_resumo["tipo_fardo"].astype(str).str.lower() != "perdas"
            ]
            df_perdas = df_resumo[
                df_resumo["tipo_fardo"].astype(str).str.lower() == "perdas"
            ]

            total_fardos_qtd = int(df_fardos["quantidade"].sum()) if not df_fardos.empty else 0
            total_fardos_peso = float(df_fardos["peso_kg"].sum()) if not df_fardos.empty else 0.0
            total_perdas_peso = float(df_perdas["perda_total_kg"].sum()) if not df_perdas.empty else 0.0
            n_fardinhos = 0
            n_fardoes = 0
            if not df_fardos.empty:
                for _, pr in df_fardos.iterrows():
                    pfa, pfi = fardos_breakdown(pr)
                    n_fardoes += pfa
                    n_fardinhos += pfi

            col_r1, col_r2, col_r3, col_r4 = st.columns(4)
            with col_r1:
                st.metric("Producao (fardos)", f"{total_fardos_qtd} un")
            with col_r2:
                st.metric("Peso Producao", formatar_peso(total_fardos_peso))
            with col_r3:
                st.metric("Perdas", formatar_peso(total_perdas_peso))
            with col_r4:
                st.metric("Fardinhos / Fardoes", f"{n_fardinhos} / {n_fardoes}")

            # ---- Eficiencia do turno (usa inicio/fim + paradas) ----
            reg_t = carregar_registro_turno(data_str, turno)
            h_ini_t = str(reg_t.get("hora_inicio", "") or "") if reg_t else ""
            h_fim_t = str(reg_t.get("hora_fim", "") or "") if reg_t else ""
            paradas_min = 0
            for p in paradas_turno:
                try:
                    paradas_min += int(float(p.get("duracao_min", 0) or 0))
                except (ValueError, TypeError):
                    pass

            dur_bruta = None
            dur_liquida = None
            kg_h = None
            if h_ini_t and h_fim_t:
                dur_bruta = duracao_minutos(h_ini_t, h_fim_t)
                if dur_bruta is not None:
                    dur_liquida = max(0, dur_bruta - paradas_min)
                    horas_liq = dur_liquida / 60
                    kg_h = (total_fardos_peso / horas_liq) if horas_liq > 0 else 0.0

            st.markdown("##### Eficiencia do Turno")
            if dur_bruta is None:
                st.info(
                    "Registre o inicio e o fim do turno (secao 'Controle de Turno' no topo) "
                    "para calcular a eficiencia."
                )
            else:
                col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                col_e1.metric("Duracao Turno", formatar_duracao(dur_bruta))
                col_e2.metric("Tempo Parado", formatar_duracao(paradas_min))
                col_e3.metric("Tempo Liquido", formatar_duracao(dur_liquida))
                col_e4.metric("Produtividade", f"{kg_h:,.0f} kg/h".replace(",", "."))

            turno_info = {
                "hora_inicio": h_ini_t,
                "hora_fim": h_fim_t,
                "duracao_bruta": dur_bruta,
                "paradas_min": paradas_min,
                "duracao_liquida": dur_liquida,
                "kg_h": kg_h,
            }

            # ---- Producao por hora ----
            st.markdown("##### Producao por Hora")
            if "hora" in df_fardos.columns and df_fardos["hora"].astype(str).str.strip().ne("").any():
                df_fh = df_fardos.copy()
                df_fh["hora"] = df_fh["hora"].astype(str).str.strip().replace("", "sem hora")
                df_fh["__fa"] = df_fh.apply(lambda r: fardos_breakdown(r)[0], axis=1)
                df_fh["__fi"] = df_fh.apply(lambda r: fardos_breakdown(r)[1], axis=1)
                por_hora = df_fh.groupby("hora").agg(
                    Fardoes=("__fa", "sum"),
                    Fardinhos=("__fi", "sum"),
                    Peso=("peso_kg", "sum"),
                ).reset_index().rename(columns={"hora": "Hora"}).sort_values("Hora")
                col_ph1, col_ph2 = st.columns([1, 1])
                with col_ph1:
                    df_ph_show = por_hora.copy()
                    df_ph_show["Peso"] = df_ph_show["Peso"].apply(formatar_peso)
                    st.dataframe(df_ph_show, use_container_width=True, hide_index=True)
                with col_ph2:
                    st.bar_chart(por_hora.set_index("Hora")["Peso"], y_label="kg")
            else:
                st.caption("Sem horarios registrados nos lancamentos deste turno.")

            # Botao PDF
            if gerar_pdf_producao_lavacao is not None:
                try:
                    pdf_bytes = gerar_pdf_producao_lavacao(
                        data_str, turno, registros_turno, paradas_turno, turno_info
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
    if turno_fixo:
        st.caption(f"Exibindo apenas paradas do Turno {turno_fixo}.")
    try:
        df_paradas = read_sheet("paradas_lavacao")
        if turno_fixo and not df_paradas.empty and "turno" in df_paradas.columns:
            df_paradas = df_paradas[df_paradas["turno"].astype(str) == turno_fixo]
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
        if turno_fixo:
            hist_turno = turno_fixo
            st.info(f"Turno: **{turno_fixo}**")
        else:
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

            # Separar fardos e perdas (Misto conta como producao)
            df_fardos_hist = df_filtrado[
                df_filtrado["tipo_fardo"].astype(str).str.lower() != "perdas"
            ]
            df_perdas_hist = df_filtrado[
                df_filtrado["tipo_fardo"].astype(str).str.lower() == "perdas"
            ]

            total_registros = len(df_fardos_hist)
            total_peso = float(df_fardos_hist["peso_kg"].sum()) if not df_fardos_hist.empty else 0.0
            total_perdas = float(df_perdas_hist["perda_total_kg"].sum()) if not df_perdas_hist.empty else 0.0
            total_fardinhos = 0
            total_fardoes = 0
            if not df_fardos_hist.empty:
                for _, pr in df_fardos_hist.iterrows():
                    pfa, pfi = fardos_breakdown(pr)
                    total_fardoes += pfa
                    total_fardinhos += pfi

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
            df_filtrado["qtd_fardao"] = df_filtrado.apply(lambda r: fardos_breakdown(r)[0], axis=1)
            df_filtrado["qtd_fardinho"] = df_filtrado.apply(lambda r: fardos_breakdown(r)[1], axis=1)

            colunas_exibir = [
                "data", "hora", "turno", "numero_op", "tipo_fardo", "nf",
                "qtd_fardao", "qtd_fardinho", "quantidade", "peso_kg",
                "perda_lixo_kg", "perda_papelao_kg",
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
