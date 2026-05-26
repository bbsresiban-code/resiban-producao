import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta

from utils.database import read_sheet, read_sheet_no_cache, append_row
from utils.formatters import formatar_data, formatar_peso

# ---------------------------------------------------------------------------
# Titulo
# ---------------------------------------------------------------------------
st.header("Ordem de Producao - Lavacao")

tab_nova, tab_consultar = st.tabs(["Nova OP", "Consultar OPs"])

# ===========================================================================
# TAB: Nova OP
# ===========================================================================
with tab_nova:
    st.subheader("Criar nova Ordem de Producao")

    with st.form("form_nova_op", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            numero_op = st.text_input("Numero da OP")
            data_op = st.date_input("Data", value=date.today())
            responsavel = st.text_input("Responsavel")
            cliente = st.text_input("Cliente")
        with col2:
            volume_ton = st.number_input("Volume (ton)", min_value=0.0, step=0.5, format="%.1f")
            produto = st.text_input("Produto")
            indice_fluidez = st.text_input("Indice de Fluidez")
            observacao = st.text_area("Observacao")

        submitted = st.form_submit_button("Criar OP", type="primary", use_container_width=True)

    if submitted:
        # Validacoes basicas
        erros = []
        if not numero_op.strip():
            erros.append("Numero da OP e obrigatorio.")
        if not responsavel.strip():
            erros.append("Responsavel e obrigatorio.")
        if not cliente.strip():
            erros.append("Cliente e obrigatorio.")
        if volume_ton <= 0:
            erros.append("Volume deve ser maior que zero.")

        if erros:
            for e in erros:
                st.error(e)
        else:
            try:
                op_data = {
                    "numero_op": numero_op.strip(),
                    "data": data_op.isoformat(),
                    "responsavel": responsavel.strip(),
                    "cliente": cliente.strip(),
                    "volume_ton": volume_ton,
                    "produto": produto.strip(),
                    "indice_fluidez": indice_fluidez.strip(),
                    "status": "aberta",
                    "observacao": observacao.strip(),
                }
                resultado = append_row("op_lavacao", op_data)
                st.session_state["op_criada_id"] = resultado["id"]
                st.session_state["op_criada_numero"] = numero_op.strip()
                st.toast("OP criada com sucesso!")
                st.success(f"OP **{numero_op}** criada com sucesso! ID: `{resultado['id']}`")
            except Exception as exc:
                st.error(f"Erro ao criar OP: {exc}")

    # -----------------------------------------------------------------------
    # Secao para adicionar NFs apos criacao da OP
    # -----------------------------------------------------------------------
    if "op_criada_id" in st.session_state:
        st.divider()
        st.subheader(f"Adicionar NFs a OP {st.session_state.get('op_criada_numero', '')}")

        with st.form("form_add_nf", clear_on_submit=True):
            col_nf1, col_nf2 = st.columns(2)
            with col_nf1:
                nf_apara = st.text_input("NF Apara")
                quant_fardos = st.number_input("Quantidade de Fardos", min_value=0, step=1)
            with col_nf2:
                peso_kg = st.number_input("Peso (kg)", min_value=0.0, step=0.5, format="%.1f")
                obs_nf = st.text_input("Observacao da NF")

            add_nf = st.form_submit_button("Adicionar NF", use_container_width=True)

        if add_nf:
            erros_nf = []
            if not nf_apara.strip():
                erros_nf.append("NF Apara e obrigatoria.")
            if quant_fardos <= 0:
                erros_nf.append("Quantidade de fardos deve ser maior que zero.")
            if peso_kg <= 0:
                erros_nf.append("Peso deve ser maior que zero.")

            if erros_nf:
                for e in erros_nf:
                    st.error(e)
            else:
                try:
                    nf_data = {
                        "op_lavacao_id": st.session_state["op_criada_id"],
                        "nf_apara": nf_apara.strip(),
                        "quant_fardos": quant_fardos,
                        "peso_kg": peso_kg,
                        "obs": obs_nf.strip(),
                    }
                    append_row("op_lavacao_nfs", nf_data)
                    st.toast("NF adicionada com sucesso!")
                    st.success(f"NF **{nf_apara}** adicionada.")
                except Exception as exc:
                    st.error(f"Erro ao adicionar NF: {exc}")

        # Mostrar NFs ja adicionadas
        try:
            df_nfs = read_sheet_no_cache("op_lavacao_nfs")
            if not df_nfs.empty:
                nfs_op = df_nfs[df_nfs["op_lavacao_id"] == st.session_state["op_criada_id"]]
                if not nfs_op.empty:
                    st.caption("NFs adicionadas a esta OP:")
                    st.dataframe(
                        nfs_op[["nf_apara", "quant_fardos", "peso_kg", "obs"]],
                        use_container_width=True,
                        hide_index=True,
                    )
        except Exception:
            pass

        if st.button("Finalizar adicao de NFs"):
            del st.session_state["op_criada_id"]
            del st.session_state["op_criada_numero"]
            st.rerun()

# ===========================================================================
# TAB: Consultar OPs
# ===========================================================================
with tab_consultar:
    st.subheader("Consultar Ordens de Producao")

    col_filtro1, col_filtro2 = st.columns(2)
    with col_filtro1:
        data_inicio = st.date_input(
            "Data Inicio",
            value=date.today() - timedelta(days=30),
            key="filtro_data_inicio",
        )
    with col_filtro2:
        data_fim = st.date_input(
            "Data Fim",
            value=date.today(),
            key="filtro_data_fim",
        )

    try:
        df_ops = read_sheet("op_lavacao")
    except Exception as exc:
        st.error(f"Erro ao carregar OPs: {exc}")
        df_ops = pd.DataFrame()

    if df_ops.empty:
        st.info("Nenhuma OP encontrada.")
    else:
        # Converter coluna data para comparacao
        df_ops["data_dt"] = pd.to_datetime(df_ops["data"], errors="coerce").dt.date
        mask = (df_ops["data_dt"] >= data_inicio) & (df_ops["data_dt"] <= data_fim)
        df_filtrado = df_ops[mask].copy()

        if df_filtrado.empty:
            st.info("Nenhuma OP encontrada no periodo selecionado.")
        else:
            # Formatar para exibicao
            df_exibir = df_filtrado[
                ["numero_op", "data", "responsavel", "cliente", "volume_ton",
                 "produto", "indice_fluidez", "status", "observacao"]
            ].copy()
            df_exibir["data"] = df_exibir["data"].apply(formatar_data)

            st.dataframe(df_exibir, use_container_width=True, hide_index=True)

            # Detalhes expandiveis com NFs
            st.subheader("Detalhes das OPs")
            try:
                df_nfs_all = read_sheet("op_lavacao_nfs")
            except Exception:
                df_nfs_all = pd.DataFrame()

            for _, row in df_filtrado.iterrows():
                with st.expander(f"OP {row['numero_op']} - {formatar_data(row['data'])} - Status: {row['status']}"):
                    col_det1, col_det2, col_det3 = st.columns(3)
                    with col_det1:
                        st.markdown(f"**Responsavel:** {row['responsavel']}")
                        st.markdown(f"**Cliente:** {row['cliente']}")
                    with col_det2:
                        st.markdown(f"**Volume:** {row['volume_ton']} ton")
                        st.markdown(f"**Produto:** {row['produto']}")
                    with col_det3:
                        st.markdown(f"**Indice Fluidez:** {row['indice_fluidez']}")
                        st.markdown(f"**Observacao:** {row.get('observacao', '')}")

                    if not df_nfs_all.empty:
                        nfs_desta_op = df_nfs_all[df_nfs_all["op_lavacao_id"] == row["id"]]
                        if not nfs_desta_op.empty:
                            st.caption("Notas Fiscais vinculadas:")
                            st.dataframe(
                                nfs_desta_op[["nf_apara", "quant_fardos", "peso_kg", "obs"]],
                                use_container_width=True,
                                hide_index=True,
                            )
                        else:
                            st.caption("Nenhuma NF vinculada a esta OP.")
                    else:
                        st.caption("Nenhuma NF vinculada a esta OP.")
