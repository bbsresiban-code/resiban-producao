import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
import pandas as pd
import uuid
from datetime import datetime

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

WORKSHEETS = [
    "op_lavacao", "op_lavacao_nfs", "producao_lavacao", "paradas_lavacao",
    "op_extrusao", "producao_extrusao", "manutencao_extrusao",
    "qualidade", "romaneio", "romaneio_itens",
]


@st.cache_resource
def get_client():
    creds_info = st.secrets["gcp_service_account"]
    creds = Credentials.from_service_account_info(dict(creds_info), scopes=SCOPES)
    return gspread.authorize(creds)


@st.cache_resource
def get_spreadsheet():
    client = get_client()
    return client.open(st.secrets["spreadsheet_name"])


def read_sheet(worksheet_name: str, ttl: int = 60) -> pd.DataFrame:
    @st.cache_data(ttl=ttl)
    def _read(ws_name: str) -> pd.DataFrame:
        sp = get_spreadsheet()
        ws = sp.worksheet(ws_name)
        data = ws.get_all_records()
        if not data:
            return pd.DataFrame()
        return pd.DataFrame(data)
    return _read(worksheet_name)


def read_sheet_no_cache(worksheet_name: str) -> pd.DataFrame:
    sp = get_spreadsheet()
    ws = sp.worksheet(worksheet_name)
    data = ws.get_all_records()
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


def append_row(worksheet_name: str, data: dict) -> dict:
    data["id"] = str(uuid.uuid4())
    data["created_at"] = datetime.now().isoformat()
    sp = get_spreadsheet()
    ws = sp.worksheet(worksheet_name)
    headers = ws.row_values(1)
    row = [data.get(h, "") for h in headers]
    ws.append_row(row, value_input_option="USER_ENTERED")
    st.cache_data.clear()
    return data


def append_rows(worksheet_name: str, rows: list[dict]) -> list[dict]:
    sp = get_spreadsheet()
    ws = sp.worksheet(worksheet_name)
    headers = ws.row_values(1)
    now = datetime.now().isoformat()
    formatted_rows = []
    for data in rows:
        data["id"] = str(uuid.uuid4())
        data["created_at"] = now
        formatted_rows.append([data.get(h, "") for h in headers])
    ws.append_rows(formatted_rows, value_input_option="USER_ENTERED")
    st.cache_data.clear()
    return rows


def update_rows(worksheet_name: str, match_col: str, match_values: list,
                update_col: str, new_value):
    sp = get_spreadsheet()
    ws = sp.worksheet(worksheet_name)
    headers = ws.row_values(1)
    match_idx = headers.index(match_col) + 1
    update_idx = headers.index(update_col) + 1
    all_values = ws.col_values(match_idx)
    cells_to_update = []
    for i, val in enumerate(all_values):
        if val in [str(v) for v in match_values]:
            cells_to_update.append(gspread.Cell(i + 1, update_idx, new_value))
    if cells_to_update:
        ws.update_cells(cells_to_update)
    st.cache_data.clear()


def proximo_sequencial(worksheet_name: str, coluna: str, prefixo: str) -> str:
    try:
        df = read_sheet(worksheet_name, ttl=10)
    except Exception:
        df = pd.DataFrame()
    if df.empty or coluna not in df.columns:
        return f"{prefixo}-0001"
    valores = df[coluna].astype(str)
    valores = valores[valores.str.startswith(prefixo)]
    if valores.empty:
        return f"{prefixo}-0001"
    numeros = []
    for v in valores:
        partes = v.rsplit("-", 1)
        if len(partes) == 2:
            try:
                numeros.append(int(partes[1]))
            except ValueError:
                pass
    if not numeros:
        return f"{prefixo}-0001"
    proximo = max(numeros) + 1
    return f"{prefixo}-{proximo:04d}"


def init_spreadsheet():
    sp = get_spreadsheet()
    existing = [ws.title for ws in sp.worksheets()]
    headers_map = {
        "op_lavacao": ["id", "numero_op", "data", "responsavel", "cliente",
                       "volume_ton", "produto", "indice_fluidez", "status",
                       "observacao", "created_at"],
        "op_lavacao_nfs": ["id", "op_lavacao_id", "nf_apara", "fornecedor",
                           "tipo_fardo", "quant_fardos", "peso_kg", "obs",
                           "created_at"],
        "producao_lavacao": ["id", "data", "turno", "numero_op", "tipo_fardo",
                             "nf", "quantidade", "peso_kg", "perda_lixo_kg",
                             "perda_papelao_kg", "perda_plastico_colorido_kg",
                             "perda_total_kg", "registrado_por", "created_at"],
        "paradas_lavacao": ["id", "data", "turno", "tipo_parada", "hora_inicio",
                            "hora_fim", "duracao_min", "observacao", "created_at"],
        "op_extrusao": ["id", "numero_op", "data", "responsavel", "cliente",
                        "volume_ton", "produto", "maquina", "data_inicio",
                        "data_final", "coordenador", "producao_final_kg",
                        "perda_percentual", "status", "observacao", "created_at"],
        "producao_extrusao": ["id", "data", "turno", "hora", "numero_op",
                              "codigo_lote", "tipo", "tipo_descricao",
                              "extrusora", "peso_kg", "mes", "ano",
                              "sequencial", "status", "observacao_lote",
                              "registrado_por", "created_at"],
        "manutencao_extrusao": ["id", "data", "turno", "troca_telas",
                                "limpeza_gaveta", "troca_facas", "observacao",
                                "created_at"],
        "qualidade": ["id", "codigo_lote", "mfi", "teor_cinzas", "densidade",
                      "umidade", "teste_filme", "grade", "cor", "local_estoque",
                      "analista", "data_analise", "observacao", "created_at"],
        "romaneio": ["id", "data", "numero_pedido", "cliente", "transportadora",
                     "placa_veiculo", "motorista", "responsavel_carregamento",
                     "nf_saida", "codigo_produto_nf", "peso_total_kg",
                     "qtd_lotes", "serial", "registrado_por", "created_at"],
        "romaneio_itens": ["id", "romaneio_id", "codigo_lote", "produto",
                           "peso_kg", "created_at"],
    }
    for ws_name, headers in headers_map.items():
        if ws_name not in existing:
            ws = sp.add_worksheet(title=ws_name, rows=1000, cols=len(headers))
            ws.update(values=[headers], range_name="A1")
        else:
            ws = sp.worksheet(ws_name)
            current = ws.row_values(1)
            if not current:
                ws.update(values=[headers], range_name="A1")
