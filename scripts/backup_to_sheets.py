"""Backup diario: copia todas as tabelas do Supabase para uma planilha Google Sheets.

Roda no GitHub Actions (ver .github/workflows/backup.yml), 1x por dia.
NAO faz parte do app ao vivo - e apenas um espelho de seguranca a cada 24h.

Variaveis de ambiente esperadas (definidas como Secrets do repositorio):
  SUPABASE_URL          - URL do projeto Supabase
  SUPABASE_KEY          - chave anon (ou service_role) do Supabase
  GCP_SERVICE_ACCOUNT   - JSON da conta de servico Google (texto completo)
  GSHEET_ID             - (opcional) ID da planilha. Se ausente, abre pelo nome GSHEET_NAME.
  GSHEET_NAME           - (opcional) nome da planilha. Padrao: "resiban-producao"
"""
import os
import json
import sys
from datetime import datetime, timezone

from supabase import create_client
import gspread
from google.oauth2.service_account import Credentials

TABELAS = [
    "aparas_estoque",
    "op_lavacao", "op_lavacao_nfs", "producao_lavacao", "paradas_lavacao",
    "op_extrusao", "producao_extrusao", "manutencao_extrusao",
    "qualidade", "romaneio", "romaneio_itens", "mistura",
]

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _cell(v):
    """Converte um valor para algo que o gspread aceita (str/num/'')."""
    if v is None:
        return ""
    if isinstance(v, (str, int, float, bool)):
        return v
    return json.dumps(v, ensure_ascii=False)


def fetch_tabela(client, tabela):
    resp = client.table(tabela).select("*").execute()
    return resp.data or []


def main():
    supabase_url = os.environ["SUPABASE_URL"]
    supabase_key = os.environ["SUPABASE_KEY"]
    sa_info = json.loads(os.environ["GCP_SERVICE_ACCOUNT"])
    gsheet_id = os.environ.get("GSHEET_ID", "").strip()
    gsheet_name = os.environ.get("GSHEET_NAME", "resiban-producao").strip()

    client = create_client(supabase_url, supabase_key)

    creds = Credentials.from_service_account_info(sa_info, scopes=SCOPES)
    gc = gspread.authorize(creds)

    sh = gc.open_by_key(gsheet_id) if gsheet_id else gc.open(gsheet_name)

    resumo = []
    for tabela in TABELAS:
        try:
            dados = fetch_tabela(client, tabela)
        except Exception as exc:
            print(f"[ERRO] {tabela}: falha ao ler do Supabase: {exc}")
            resumo.append((tabela, "ERRO leitura"))
            continue

        # Cabecalho: uniao das chaves preservando ordem da 1a linha
        if dados:
            headers = list(dados[0].keys())
            for linha in dados:
                for k in linha.keys():
                    if k not in headers:
                        headers.append(k)
            matriz = [headers] + [[_cell(linha.get(h)) for h in headers] for linha in dados]
        else:
            matriz = [["(sem registros)"]]

        try:
            ws = sh.worksheet(tabela)
            ws.clear()
        except gspread.WorksheetNotFound:
            n_rows = max(len(matriz) + 10, 100)
            n_cols = max(len(matriz[0]) + 5, 26)
            ws = sh.add_worksheet(title=tabela, rows=n_rows, cols=n_cols)

        ws.update(matriz, value_input_option="RAW")
        print(f"[OK] {tabela}: {len(dados)} registros")
        resumo.append((tabela, f"{len(dados)} registros"))

    # Aba de controle com timestamp do ultimo backup
    ts = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S %Z")
    info = [["Ultimo backup", ts], ["Tabela", "Status"]] + [[t, s] for t, s in resumo]
    try:
        ws_info = sh.worksheet("_backup_info")
        ws_info.clear()
    except gspread.WorksheetNotFound:
        ws_info = sh.add_worksheet(title="_backup_info", rows=50, cols=4)
    ws_info.update(info, value_input_option="RAW")

    print(f"Backup concluido em {ts}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FALHA no backup: {exc}")
        sys.exit(1)
