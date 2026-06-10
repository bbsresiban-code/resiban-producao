import pandas as pd
from utils.database import read_sheet_fresh

TIPOS = {
    "01": "Produto Proprio",
    "02": "Servico/Terceiros",
    "04": "Revenda",
    "06": "Mistura",
}


def gerar_codigo_serial(tipo: str, extrusora: str, data_producao) -> tuple[str, int]:
    mes = data_producao.month
    ano = data_producao.year % 100

    df = read_sheet_fresh("producao_extrusao")

    if df.empty:
        proximo_seq = 1
    else:
        df["mes"] = pd.to_numeric(df["mes"], errors="coerce")
        df["ano"] = pd.to_numeric(df["ano"], errors="coerce")
        df["sequencial"] = pd.to_numeric(df["sequencial"], errors="coerce")

        filtro = (
            (df["mes"] == mes) &
            (df["ano"] == ano)
        )
        subset = df[filtro]

        if subset.empty:
            proximo_seq = 1
        else:
            proximo_seq = int(subset["sequencial"].max()) + 1

    codigo = f"{tipo}-{mes:02d}-{ano:02d}-{proximo_seq:03d}-{extrusora}"
    return codigo, proximo_seq


def preview_codigo(tipo: str, extrusora: str, data_producao) -> str:
    mes = data_producao.month
    ano = data_producao.year % 100
    return f"{tipo}-{mes:02d}-{ano:02d}-???-{extrusora}"
