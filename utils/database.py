import streamlit as st
import pandas as pd
import uuid
import threading
from datetime import datetime
from supabase import create_client, Client

# Schema atual da tabela aparas_estoque:
# id, numero_nf, fornecedor, tipo_material (Proprio/Servico), tipo_fardo,
# quantidade, peso_kg, data_recebimento, qualidade, status, opl_em_uso,
# data_classificacao, classificado_por, registrado_por, observacao, created_at

WORKSHEETS = [
    "aparas_estoque",
    "op_lavacao", "op_lavacao_nfs", "producao_lavacao", "paradas_lavacao",
    "op_extrusao", "producao_extrusao", "manutencao_extrusao",
    "qualidade", "romaneio", "romaneio_itens", "mistura",
]

# TTL (segundos) do cache de leitura. Baixo de proposito: e apenas uma rede de
# seguranca para mudancas feitas direto no banco (fora do app). Mudancas feitas
# PELO app invalidam o cache na hora via _bump_version (ver abaixo).
CACHE_TTL = 15


@st.cache_resource
def get_client() -> Client:
    url = st.secrets["supabase"]["url"]
    key = st.secrets["supabase"]["key"]
    return create_client(url, key)


# ---------------------------------------------------------------------------
# Versionamento GLOBAL do cache (compartilhado entre TODAS as sessoes)
# ---------------------------------------------------------------------------
# O Streamlit Cloud roda em um unico processo, entao um dict de modulo e visto
# por todas as sessoes/usuarios. Guardar a versao aqui (e nao no session_state)
# faz com que, quando QUALQUER usuario grava em uma tabela, o cache daquela
# tabela seja invalidado para TODOS imediatamente. Assim, uma OPL criada pelo
# master aparece na hora para o operador lancar producao, etc.
_TABLE_VERSIONS: dict[str, int] = {}
_VERSIONS_LOCK = threading.Lock()


def _get_version(table: str) -> int:
    return _TABLE_VERSIONS.get(table, 0)


def _bump_version(table: str):
    with _VERSIONS_LOCK:
        _TABLE_VERSIONS[table] = _TABLE_VERSIONS.get(table, 0) + 1


def _query_table(table: str) -> pd.DataFrame:
    """Consulta direta ao Supabase (sem cache)."""
    client = get_client()
    response = client.table(table).select("*").execute()
    data = response.data or []
    if not data:
        return pd.DataFrame()
    return pd.DataFrame(data)


@st.cache_data(ttl=CACHE_TTL)
def _read_table_cached(table: str, _version: int) -> pd.DataFrame:
    # _version entra na chave do cache: quando _bump_version incrementa, a
    # proxima leitura tem chave nova -> cache miss -> dados frescos.
    return _query_table(table)


def read_sheet(worksheet_name: str, ttl: int = CACHE_TTL) -> pd.DataFrame:
    """Leitura com cache curto, invalidado na hora por gravacoes do app."""
    version = _get_version(worksheet_name)
    return _read_table_cached(worksheet_name, version)


def read_sheet_no_cache(worksheet_name: str) -> pd.DataFrame:
    """Leitura SEMPRE fresca, direto do Supabase (sem cache nenhum).

    Usar em fluxos onde o dado tem que aparecer imediatamente: selecao de OPs
    abertas, fardos ja lancados, geracao de sequenciais/codigo de lote, etc.
    """
    return _query_table(worksheet_name)


def _serialize_value(v):
    if v is None:
        return None
    if isinstance(v, str):
        return v if v.strip() else None
    if isinstance(v, (int, float, bool)):
        return v
    if hasattr(v, "isoformat"):
        return v.isoformat()
    return str(v)


def _serialize_row(data: dict) -> dict:
    return {k: _serialize_value(v) for k, v in data.items()}


def append_row(worksheet_name: str, data: dict) -> dict:
    data["id"] = str(uuid.uuid4())
    data.setdefault("created_at", datetime.now().isoformat())
    payload = _serialize_row(data)
    client = get_client()
    client.table(worksheet_name).insert(payload).execute()
    _bump_version(worksheet_name)
    return data


def append_rows(worksheet_name: str, rows: list[dict]) -> list[dict]:
    now = datetime.now().isoformat()
    payloads = []
    for data in rows:
        data["id"] = str(uuid.uuid4())
        data.setdefault("created_at", now)
        payloads.append(_serialize_row(data))
    client = get_client()
    client.table(worksheet_name).insert(payloads).execute()
    _bump_version(worksheet_name)
    return rows


def update_rows(worksheet_name: str, match_col: str, match_values: list,
                update_col: str, new_value):
    client = get_client()
    str_values = [str(v) for v in match_values]
    client.table(worksheet_name).update({update_col: _serialize_value(new_value)}).in_(match_col, str_values).execute()
    _bump_version(worksheet_name)


def update_row_multi(worksheet_name: str, match_col: str, match_value,
                     updates: dict):
    client = get_client()
    payload = _serialize_row(updates)
    client.table(worksheet_name).update(payload).eq(match_col, str(match_value)).execute()
    _bump_version(worksheet_name)


def proximo_sequencial(worksheet_name: str, coluna: str, prefixo: str) -> str:
    # Leitura fresca: evita gerar numeros duplicados (OPL/OPE/ROM/MIX).
    try:
        df = read_sheet_no_cache(worksheet_name)
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
    """Compatibilidade: tabelas sao criadas via SQL no Supabase."""
    pass
