def validar_peso(peso: float, campo: str = "Peso") -> str | None:
    if peso is None or peso <= 0:
        return f"{campo} deve ser maior que zero."
    return None


def validar_obrigatorio(valor, campo: str) -> str | None:
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        return f"{campo} e obrigatorio."
    return None


def validar_perdas(peso_fardos: float, perda_total: float) -> str | None:
    if perda_total > peso_fardos:
        return "Total de perdas nao pode ser maior que o peso dos fardos."
    return None


def validar_hora(hora: str) -> str | None:
    if not hora or ":" not in hora:
        return "Hora invalida. Use formato HH:MM."
    try:
        h, m = hora.split(":")
        if not (0 <= int(h) <= 23 and 0 <= int(m) <= 59):
            return "Hora fora do intervalo valido."
    except ValueError:
        return "Hora invalida. Use formato HH:MM."
    return None
