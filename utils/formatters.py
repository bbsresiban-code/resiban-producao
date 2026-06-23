from __future__ import annotations

from datetime import date, datetime


def formatar_peso(valor: float) -> str:
    return f"{valor:,.1f} kg".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_data(d) -> str:
    if isinstance(d, str):
        try:
            d = datetime.fromisoformat(d).date()
        except ValueError:
            return d
    if isinstance(d, (date, datetime)):
        return d.strftime("%d/%m/%Y")
    return str(d)


def formatar_percentual(valor: float) -> str:
    return f"{valor:.1f}%".replace(".", ",")


TURNOS = ["A", "B", "C"]

TIPOS_FARDO = ["Fardinho", "Fardao"]


def _fardo_to_int(v) -> int:
    """Converte valor (str/num/None/NaN) para int de forma segura."""
    try:
        if v is None:
            return 0
        s = str(v).strip()
        if s == "" or s.lower() == "nan":
            return 0
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def fardos_breakdown(row) -> tuple[int, int]:
    """Retorna (qtd_fardao, qtd_fardinho) de uma linha (dict ou Series).

    Retrocompativel: se as colunas qtd_fardao/qtd_fardinho nao existirem ou
    estiverem zeradas (linhas antigas), deriva do tipo_fardo + quantidade.
    """
    get = row.get if hasattr(row, "get") else (lambda k, d=None: row[k] if k in row else d)
    fa = _fardo_to_int(get("qtd_fardao"))
    fi = _fardo_to_int(get("qtd_fardinho"))
    if fa == 0 and fi == 0:
        total = _fardo_to_int(get("quantidade"))
        if total == 0:
            total = _fardo_to_int(get("quant_fardos"))
        tipo = str(get("tipo_fardo", "") or "").strip().lower()
        if tipo == "fardao":
            fa = total
        elif tipo == "fardinho":
            fi = total
    return fa, fi


def tipo_fardo_label(qtd_fardao, qtd_fardinho) -> str:
    """Rotulo do tipo de fardo a partir das quantidades: Fardao/Fardinho/Misto."""
    fa = _fardo_to_int(qtd_fardao)
    fi = _fardo_to_int(qtd_fardinho)
    if fa > 0 and fi > 0:
        return "Misto"
    if fa > 0:
        return "Fardao"
    if fi > 0:
        return "Fardinho"
    return ""


def formatar_fardos(qtd_fardao, qtd_fardinho) -> str:
    """Texto curto do breakdown, ex: '10 fardoes + 25 fardinhos'."""
    fa = _fardo_to_int(qtd_fardao)
    fi = _fardo_to_int(qtd_fardinho)
    partes = []
    if fa > 0:
        partes.append(f"{fa} " + ("fardoes" if fa != 1 else "fardao"))
    if fi > 0:
        partes.append(f"{fi} " + ("fardinhos" if fi != 1 else "fardinho"))
    return " + ".join(partes) if partes else "0"

TIPOS_PRODUTO = {
    "01": "Produto Proprio",
    "02": "Servico/Terceiros",
    "04": "Revenda",
    "06": "Mistura",
}

EXTRUSORAS = ["A", "B"]

GRADES = [
    "RESI01C",
    "RESI02CI",
    "RESI03CR",
    "RESI04CS",
    "RESI05CO",
    "RESI06S",
]

CORES = [
    "C1", "C2", "C3",
    "M1", "M2", "M3",
    "EM1", "EM2", "EM3",
    "E1", "E2", "E3",
]

TIPOS_PARADA = [
    "Manutencao Corretiva",
    "Corretiva Programada",
    "Manutencao Preventiva",
]


def formatar_duracao(minutos) -> str:
    """Converte minutos em texto 'HhMM' (ex.: 488 -> '8h08'). '-' se invalido."""
    try:
        m = int(round(float(minutos)))
    except (ValueError, TypeError):
        return "-"
    if m < 0:
        return "-"
    h, mm = divmod(m, 60)
    return f"{h}h{mm:02d}"

LOCAIS_ESTOQUE = [
    "A1", "A2", "A3", "A4", "A5", "A6",
    "A7", "A8", "A9", "A10", "A11", "A12",
    "EXPED.", "QUALIDADE",
]
