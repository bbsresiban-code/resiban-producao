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

TIPOS_PRODUTO = {
    "01": "Produto Proprio",
    "02": "Servico/Terceiros",
    "04": "Revenda",
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
    "Quebra",
    "Manutencao Corretiva",
    "Manutencao Preventiva Programada",
]

LOCAIS_ESTOQUE = [
    "A1", "A2", "A3", "A4", "A5", "A6",
    "A7", "A8", "A9", "A10", "A11", "A12",
    "EXPED.", "QUALIDADE",
]
