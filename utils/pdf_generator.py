"""
Gerador de PDFs para o sistema de gestao da fabrica de reciclagem de plasticos.
Resiban - Resinas Bandeirante LTDA / Grupo CRB

Todos os textos em Portugues (BR).
Utiliza fpdf2 para geracao dos documentos.
"""

import os
from fpdf import FPDF
from io import BytesIO

LOGO_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "logo.png")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_pdf() -> FPDF:
    """Cria instancia FPDF padrao A4, margens 15 mm, fonte Helvetica."""
    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.set_margins(15, 15, 15)
    pdf.add_page()
    pdf.set_font("Helvetica", size=10)
    return pdf


def _header(pdf: FPDF, title: str) -> None:
    """Adiciona cabecalho padrao: logo, empresa, grupo e titulo do documento."""
    if os.path.exists(LOGO_PATH):
        logo_x = pdf.l_margin
        logo_y = pdf.get_y()
        pdf.image(LOGO_PATH, x=logo_x, y=logo_y, w=35)
        text_x = logo_x + 40
        pdf.set_xy(text_x, logo_y)
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(pdf.w - pdf.r_margin - text_x, 8, "RESIBAN - Resinas Bandeirante LTDA", new_x="LMARGIN", new_y="NEXT")
        pdf.set_x(text_x)
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(pdf.w - pdf.r_margin - text_x, 6, "Grupo CRB", new_x="LMARGIN", new_y="NEXT")
        pdf.set_y(logo_y + 25)
    else:
        pdf.set_font("Helvetica", "B", 16)
        pdf.cell(0, 8, "RESIBAN - Resinas Bandeirante LTDA", align="C", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("Helvetica", "", 11)
        pdf.cell(0, 6, "Grupo CRB", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 8, title, align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)
    pdf.set_font("Helvetica", size=10)


def _add_field(pdf: FPDF, label: str, value: str) -> None:
    """Adiciona um campo label: valor em uma linha."""
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(50, 7, f"{label}:", new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, str(value) if value is not None else "", new_x="LMARGIN", new_y="NEXT")


def _draw_table_header(pdf: FPDF, headers: list[str], col_widths: list[float]) -> None:
    """Desenha cabecalho da tabela na posicao atual."""
    x_start = pdf.l_margin
    y = pdf.get_y()
    pdf.set_font("Helvetica", "B", 8)
    for i, header in enumerate(headers):
        x = x_start + sum(col_widths[:i])
        pdf.rect(x, y, col_widths[i], 7)
        pdf.set_xy(x, y)
        pdf.cell(col_widths[i], 7, header, align="C")
    pdf.set_xy(x_start, y + 7)


def _add_table(pdf: FPDF, headers: list[str], rows: list[list[str]], col_widths: list[float] | None = None) -> None:
    """Desenha tabela com bordas usando posicionamento absoluto."""
    usable_width = pdf.w - pdf.l_margin - pdf.r_margin
    if col_widths is None:
        n = len(headers)
        col_widths = [usable_width / n] * n

    _draw_table_header(pdf, headers, col_widths)

    pdf.set_font("Helvetica", "", 8)
    row_height = 7
    x_start = pdf.l_margin

    for row in rows:
        if pdf.get_y() + row_height > pdf.h - 20:
            pdf.add_page()
            _draw_table_header(pdf, headers, col_widths)
            pdf.set_font("Helvetica", "", 8)

        y = pdf.get_y()
        for i, cell in enumerate(row):
            x = x_start + sum(col_widths[:i])
            text = str(cell) if cell is not None else ""
            pdf.rect(x, y, col_widths[i], row_height)
            pdf.set_xy(x, y)
            pdf.cell(col_widths[i], row_height, text, align="C")
        pdf.set_xy(x_start, y + row_height)


def _section_title(pdf: FPDF, title: str) -> None:
    """Adiciona titulo de secao."""
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, title, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)


def _to_bytes(pdf: FPDF) -> bytes:
    """Converte FPDF em bytes via BytesIO."""
    buffer = BytesIO()
    pdf.output(buffer)
    return buffer.getvalue()


# ---------------------------------------------------------------------------
# 1. Ordem de Producao - Lavacao
# ---------------------------------------------------------------------------

def gerar_pdf_op_lavacao(op_data: dict, nfs: list[dict]) -> bytes:
    """
    Gera PDF da Ordem de Producao de Lavacao.

    op_data keys esperadas: numero_op, data, responsavel, cliente, volume,
                            produto, indice_fluidez, observacao
    nfs item keys: nf_apara, quant_fardos, peso, obs
    """
    pdf = _create_pdf()
    numero = op_data.get("numero_op", "")
    _header(pdf, f"ORDEM DE PRODUCAO LAVACAO - OP {numero}")

    _add_field(pdf, "Numero OP", op_data.get("numero_op", ""))
    _add_field(pdf, "Data", op_data.get("data", ""))
    _add_field(pdf, "Responsavel", op_data.get("responsavel", ""))
    _add_field(pdf, "Cliente", op_data.get("cliente", ""))
    _add_field(pdf, "Volume (ton)", op_data.get("volume_ton", op_data.get("volume", "")))
    _add_field(pdf, "Produto", op_data.get("produto", ""))
    _add_field(pdf, "Indice de Fluidez", op_data.get("indice_fluidez", ""))
    _add_field(pdf, "Observacao", op_data.get("observacao", ""))

    pdf.ln(4)

    _section_title(pdf, "Notas Fiscais de Apara")

    headers = ["NF Apara", "Fornecedor", "Qtd Fardos", "Peso (kg)", "Obs"]
    col_widths = [35, 40, 25, 30, 50]
    rows = []
    total_peso = 0.0
    total_fardos = 0
    for nf in (nfs or []):
        peso = nf.get("peso_kg", nf.get("peso", 0)) or 0
        fardos = nf.get("quant_fardos", 0) or 0
        total_peso += float(peso)
        total_fardos += int(fardos)
        rows.append([
            str(nf.get("nf_apara", "")),
            str(nf.get("fornecedor", "")),
            str(fardos),
            str(peso),
            str(nf.get("obs", "")),
        ])

    _add_table(pdf, headers, rows, col_widths)

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, f"Total NFs: {len(nfs or [])} | Total Fardos: {total_fardos} | Peso Total: {total_peso:,.1f} kg", new_x="LMARGIN", new_y="NEXT")

    return _to_bytes(pdf)


# ---------------------------------------------------------------------------
# 1b. Fechamento de OP Lavacao (completo)
# ---------------------------------------------------------------------------

def gerar_pdf_fechamento_op_lavacao(
    op_data: dict, nfs: list[dict], producao_por_nf: list[dict], perdas: dict
) -> bytes:
    pdf = _create_pdf()
    numero = op_data.get("numero_op", "")
    _header(pdf, f"FECHAMENTO DE OP LAVACAO - {numero}")

    pdf.set_font("Helvetica", "", 9)
    col_left = 90
    col_right = pdf.w - pdf.l_margin - pdf.r_margin - col_left
    y_start = pdf.get_y()

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(35, 5, "Numero OP:", new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(55, 5, numero, new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(20, 5, "Data:", new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, str(op_data.get("data", "")), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(35, 5, "Responsavel:", new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(55, 5, str(op_data.get("responsavel", "")), new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(20, 5, "Cliente:", new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, str(op_data.get("cliente", "")), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(35, 5, "Volume (ton):", new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(55, 5, str(op_data.get("volume_ton", op_data.get("volume", ""))), new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(20, 5, "Produto:", new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, str(op_data.get("produto", "")), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(35, 5, "Indice Fluidez:", new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(55, 5, str(op_data.get("indice_fluidez", "")), new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "B", 9)
    pdf.cell(20, 5, "Status:", new_x="END", new_y="TOP")
    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "FECHADA", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Notas Fiscais de Apara", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    headers_nf = ["NF", "Fornecedor", "Tipo", "Qtd", "Peso (kg)"]
    col_w_nf = [30, 50, 25, 25, 50]
    rows_nf = []
    for nf in (nfs or []):
        rows_nf.append([
            str(nf.get("nf_apara", "")),
            str(nf.get("fornecedor", "")),
            str(nf.get("tipo_fardo", "")),
            str(nf.get("quant_fardos", "")),
            str(nf.get("peso_kg", "")),
        ])
    _add_table(pdf, headers_nf, rows_nf, col_w_nf)
    pdf.ln(3)

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Producao Realizada por NF", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    headers_prod = ["NF", "Tipo", "Qtd Plan.", "Qtd Real.", "Peso Plan.", "Peso Real.", "% Concl."]
    col_w_prod = [25, 22, 23, 23, 27, 27, 22]
    rows_prod = []
    for p in (producao_por_nf or []):
        rows_prod.append([
            str(p.get("nf", "")),
            str(p.get("tipo", "")),
            str(p.get("qtd_plan", "")),
            str(p.get("qtd_real", "")),
            str(p.get("peso_plan", "")),
            str(p.get("peso_real", "")),
            f"{p.get('perc', 0):.1f}%",
        ])
    _add_table(pdf, headers_prod, rows_prod, col_w_prod)
    pdf.ln(3)

    peso_entrada = perdas.get('peso_entrada', 0)
    perda_total = perdas.get('total', 0)
    perc_perda = perdas.get('percentual', 0)
    peso_liq = peso_entrada - perda_total

    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "Perdas e Resumo Final", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)
    headers_res = ["Lixo (kg)", "Papelao (kg)", "Pl. Colorido (kg)", "Total Perdas (kg)", "% Perda", "Peso Entrada (kg)", "Peso Liquido (kg)"]
    col_w_res = [24, 24, 28, 28, 20, 28, 28]
    rows_res = [[
        f"{perdas.get('lixo', 0):.1f}",
        f"{perdas.get('papelao', 0):.1f}",
        f"{perdas.get('colorido', 0):.1f}",
        f"{perda_total:.1f}",
        f"{perc_perda:.1f}%",
        f"{peso_entrada:.1f}",
        f"{peso_liq:.1f}",
    ]]
    _add_table(pdf, headers_res, rows_res, col_w_res)

    y_remaining = pdf.h - 20 - pdf.get_y()
    if y_remaining < 25:
        pdf.add_page()
    pdf.ln(max(10, y_remaining - 15))

    line_width = 70
    gap = (pdf.w - pdf.l_margin - pdf.r_margin - 2 * line_width) / 3
    y_sig = pdf.get_y()
    pdf.set_font("Helvetica", "", 9)
    x1 = pdf.l_margin + gap
    pdf.line(x1, y_sig, x1 + line_width, y_sig)
    pdf.set_xy(x1, y_sig + 2)
    pdf.cell(line_width, 5, "Responsavel", align="C")
    x2 = x1 + line_width + gap
    pdf.line(x2, y_sig, x2 + line_width, y_sig)
    pdf.set_xy(x2, y_sig + 2)
    pdf.cell(line_width, 5, "Gerente de Producao", align="C")

    return _to_bytes(pdf)


# ---------------------------------------------------------------------------
# 2. Controle de Producao - Lavacao
# ---------------------------------------------------------------------------

def gerar_pdf_producao_lavacao(
    data: str,
    turno: str,
    registros: list[dict],
    paradas: list[dict],
) -> bytes:
    """
    Gera PDF do Controle de Producao de Lavacao.

    registros item keys: tipo (fardinhos|fardoes), op, nf, quantidade, peso,
                         lixo, papelao, plastico_colorido, total_perda, perc_perda
    paradas item keys: tipo, inicio, fim, duracao, obs
    """
    pdf = _create_pdf()
    _header(pdf, "CONTROLE DE PRODUCAO LAVACAO")

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(90, 7, f"Data: {data}", new_x="END", new_y="TOP")
    pdf.cell(0, 7, f"Turno: {turno}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    registros = registros or []

    # Fardinhos
    fardinhos = [r for r in registros if str(r.get("tipo_fardo", r.get("tipo", ""))).lower() == "fardinho"]
    _section_title(pdf, "Fardinhos")
    headers_f = ["OP", "NF", "Quantidade", "Peso (kg)"]
    col_widths_f = [40, 45, 40, 55]
    rows_f = [
        [str(r.get("numero_op", r.get("op", ""))), str(r.get("nf", "")),
         str(r.get("quantidade", "")), str(r.get("peso_kg", r.get("peso", "")))]
        for r in fardinhos
    ]
    _add_table(pdf, headers_f, rows_f, col_widths_f)

    # Fardoes
    fardoes = [r for r in registros if str(r.get("tipo_fardo", r.get("tipo", ""))).lower() == "fardao"]
    _section_title(pdf, "Fardoes")
    rows_fd = [
        [str(r.get("numero_op", r.get("op", ""))), str(r.get("nf", "")),
         str(r.get("quantidade", "")), str(r.get("peso_kg", r.get("peso", "")))]
        for r in fardoes
    ]
    _add_table(pdf, headers_f, rows_fd, col_widths_f)

    # Perdas
    perdas = [r for r in registros if str(r.get("tipo_fardo", r.get("tipo", ""))).lower() == "perdas"]
    _section_title(pdf, "Perdas")
    if perdas:
        p = perdas[0]
        _add_field(pdf, "Lixo (kg)", p.get("perda_lixo_kg", p.get("lixo", "0")))
        _add_field(pdf, "Papelao (kg)", p.get("perda_papelao_kg", p.get("papelao", "0")))
        _add_field(pdf, "Plastico Colorido (kg)", p.get("perda_plastico_colorido_kg", p.get("plastico_colorido", "0")))
        _add_field(pdf, "Total Perda (kg)", p.get("perda_total_kg", p.get("total_perda", "0")))
    else:
        pdf.cell(0, 7, "Nenhuma perda registrada.", new_x="LMARGIN", new_y="NEXT")

    # Paradas
    paradas = paradas or []
    _section_title(pdf, "Paradas")
    if paradas:
        headers_p = ["Tipo", "Inicio", "Fim", "Duracao (min)", "Obs"]
        col_widths_p = [45, 25, 25, 30, 55]
        rows_p = [
            [str(p.get("tipo_parada", p.get("tipo", ""))),
             str(p.get("hora_inicio", p.get("inicio", ""))),
             str(p.get("hora_fim", p.get("fim", ""))),
             str(p.get("duracao_min", p.get("duracao", ""))),
             str(p.get("observacao", p.get("obs", "")))]
            for p in paradas
        ]
        _add_table(pdf, headers_p, rows_p, col_widths_p)
    else:
        pdf.cell(0, 7, "Nenhuma parada registrada.", new_x="LMARGIN", new_y="NEXT")

    return _to_bytes(pdf)


# ---------------------------------------------------------------------------
# 3. Ordem de Producao - Extrusao
# ---------------------------------------------------------------------------

def gerar_pdf_op_extrusao(op_data: dict, lotes: list[dict]) -> bytes:
    """
    Gera PDF da Ordem de Producao de Extrusao.

    op_data keys esperadas: numero_op, data, responsavel, cliente, volume,
                            produto, maquina, coordenador, observacao
    lotes item keys: lote, extrusora, peso
    """
    pdf = _create_pdf()
    numero = op_data.get("numero_op", "")
    _header(pdf, f"ORDEM DE PRODUCAO EXTRUSAO - OP {numero}")

    _add_field(pdf, "Numero OP", op_data.get("numero_op", ""))
    _add_field(pdf, "Data", op_data.get("data", ""))
    _add_field(pdf, "Responsavel", op_data.get("responsavel", ""))
    _add_field(pdf, "Cliente", op_data.get("cliente", ""))
    _add_field(pdf, "Volume (ton)", op_data.get("volume_ton", op_data.get("volume", "")))
    _add_field(pdf, "Produto", op_data.get("produto", ""))
    _add_field(pdf, "Maquina", op_data.get("maquina", ""))
    _add_field(pdf, "Coordenador", op_data.get("coordenador", ""))
    _add_field(pdf, "Observacao", op_data.get("observacao", ""))

    pdf.ln(4)

    # Tabela de lotes produzidos
    _section_title(pdf, "Lotes Produzidos")

    headers = ["Lote", "Extrusora", "Peso (kg)"]
    col_widths = [60, 60, 60]
    rows = []
    total_peso = 0.0
    for lote in (lotes or []):
        peso = lote.get("peso_kg", lote.get("peso", 0)) or 0
        total_peso += float(peso)
        rows.append([
            str(lote.get("codigo_lote", lote.get("lote", ""))),
            str(lote.get("extrusora", "")),
            str(peso),
        ])

    _add_table(pdf, headers, rows, col_widths)

    # Producao final e perda
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, f"Producao Final: {total_peso:,.2f} kg", new_x="LMARGIN", new_y="NEXT")

    volume_str = op_data.get("volume", "0") or "0"
    try:
        volume_ton = float(str(volume_str).replace(",", "."))
        volume_kg = volume_ton * 1000
    except (ValueError, TypeError):
        volume_kg = 0.0

    if volume_kg > 0:
        perda_kg = volume_kg - total_peso
        perda_perc = (perda_kg / volume_kg) * 100 if perda_kg > 0 else 0.0
        pdf.cell(0, 7, f"Perda: {perda_perc:.2f}%", new_x="LMARGIN", new_y="NEXT")
    else:
        pdf.cell(0, 7, "Perda: -", new_x="LMARGIN", new_y="NEXT")

    return _to_bytes(pdf)


# ---------------------------------------------------------------------------
# 4. Relatorio Diario de Extrusao
# ---------------------------------------------------------------------------

def gerar_pdf_producao_extrusao(
    data: str,
    turno: str,
    registros: list[dict],
    manutencao: list[dict],
) -> bytes:
    """
    Gera PDF do Relatorio Diario de Extrusao.

    registros item keys: hora, lote, extrusora, peso, op, obs
    manutencao item keys: troca_telas, limpeza_gaveta, troca_facas, obs
    """
    pdf = _create_pdf()
    _header(pdf, "RELATORIO DIARIO DE EXTRUSAO")

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(90, 7, f"Data: {data}", new_x="END", new_y="TOP")
    pdf.cell(0, 7, f"Turno: {turno}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    # Tabela de registros
    _section_title(pdf, "Producao")
    headers = ["Hora", "Lote", "Extrusora", "Peso (kg)", "OP", "Obs"]
    col_widths = [25, 35, 30, 30, 25, 35]
    rows = [
        [str(r.get("hora", "")), str(r.get("codigo_lote", r.get("lote", ""))),
         str(r.get("extrusora", "")), str(r.get("peso_kg", r.get("peso", ""))),
         str(r.get("numero_op", r.get("op", ""))), str(r.get("observacao_lote", r.get("obs", "")))]
        for r in (registros or [])
    ]
    _add_table(pdf, headers, rows, col_widths)

    # Manutencao
    _section_title(pdf, "Manutencao")
    manutencao = manutencao or []
    if manutencao:
        headers_m = ["Troca Telas", "Limpeza Gaveta", "Troca Facas", "Obs"]
        col_widths_m = [40, 45, 40, 55]
        rows_m = [
            [str(m.get("troca_telas", "")), str(m.get("limpeza_gaveta", "")),
             str(m.get("troca_facas", "")), str(m.get("obs", ""))]
            for m in manutencao
        ]
        _add_table(pdf, headers_m, rows_m, col_widths_m)
    else:
        pdf.cell(0, 7, "Nenhuma manutencao registrada.", new_x="LMARGIN", new_y="NEXT")

    return _to_bytes(pdf)


# ---------------------------------------------------------------------------
# 5. Romaneio de Carregamento
# ---------------------------------------------------------------------------

def gerar_pdf_romaneio(romaneio: dict, itens: list[dict]) -> bytes:
    """
    Gera PDF do Romaneio de Carregamento de Produto Acabado.

    romaneio keys: numero_pedido, data, cliente, transportadora, placa,
                   motorista, responsavel
    itens item keys: lote, produto, peso
    """
    pdf = _create_pdf()
    _header(pdf, "ROMANEIO DE CARREGAMENTO DE PRODUTO ACABADO")

    _add_field(pdf, "Numero Pedido", romaneio.get("numero_pedido", ""))
    _add_field(pdf, "Data", romaneio.get("data", ""))
    _add_field(pdf, "Cliente", romaneio.get("cliente", ""))
    _add_field(pdf, "Transportadora", romaneio.get("transportadora", ""))
    _add_field(pdf, "Placa", romaneio.get("placa_veiculo", romaneio.get("placa", "")))
    _add_field(pdf, "Motorista", romaneio.get("motorista", ""))
    _add_field(pdf, "Responsavel", romaneio.get("responsavel_carregamento", romaneio.get("responsavel", "")))

    pdf.ln(4)

    # Tabela de lotes
    _section_title(pdf, "Itens do Carregamento")
    headers = ["Lote", "Produto (Grade + Cor)", "Peso (kg)"]
    col_widths = [50, 75, 55]
    rows = []
    total_peso = 0.0
    for item in (itens or []):
        peso = item.get("peso_kg", item.get("peso", 0)) or 0
        total_peso += float(peso)
        rows.append([
            str(item.get("codigo_lote", item.get("lote", ""))),
            str(item.get("produto", "")),
            str(peso),
        ])

    _add_table(pdf, headers, rows, col_widths)

    # Totais
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, f"Quantidade de Lotes: {len(itens or [])}", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, f"Peso Total: {total_peso:,.2f} kg", new_x="LMARGIN", new_y="NEXT")

    # Assinaturas
    pdf.ln(20)
    line_width = 70
    gap = (pdf.w - pdf.l_margin - pdf.r_margin - 2 * line_width) / 3
    y_sig = pdf.get_y()

    pdf.set_font("Helvetica", "", 9)

    x1 = pdf.l_margin + gap
    pdf.line(x1, y_sig, x1 + line_width, y_sig)
    pdf.set_xy(x1, y_sig + 2)
    pdf.cell(line_width, 5, "Responsavel", align="C")

    x2 = x1 + line_width + gap
    pdf.line(x2, y_sig, x2 + line_width, y_sig)
    pdf.set_xy(x2, y_sig + 2)
    pdf.cell(line_width, 5, "Motorista", align="C")

    return _to_bytes(pdf)


# ---------------------------------------------------------------------------
# 6. Laudo Tecnico de Qualidade
# ---------------------------------------------------------------------------

def gerar_pdf_laudo_tecnico(romaneio: dict, itens_qualidade: list[dict]) -> bytes:
    """
    Gera PDF do Laudo Tecnico de Qualidade.

    romaneio keys: numero_pedido (ou numero_romaneio), cliente, data
    itens_qualidade item keys: lote, grade, cor, mfi, teor_cinzas, densidade,
                               umidade, teste_filme
    """
    pdf = _create_pdf()
    _header(pdf, "LAUDO TECNICO DE QUALIDADE")

    numero = romaneio.get("numero_romaneio", romaneio.get("numero_pedido", ""))
    cliente = romaneio.get("cliente", "")
    data_doc = romaneio.get("data", "")

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(
        0, 7,
        f"Referente ao Romaneio {numero} - Cliente: {cliente}",
        align="C", new_x="LMARGIN", new_y="NEXT",
    )
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"Data: {data_doc}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(6)

    # Tabela de qualidade por lote
    headers = [
        "Lote", "Grade", "Cor", "MFI", "Teor Cinzas",
        "Densidade", "Umidade", "Teste Filme",
    ]
    col_widths = [22, 22, 20, 20, 25, 22, 22, 27]

    rows = [
        [
            str(item.get("codigo_lote", item.get("lote", ""))),
            str(item.get("grade", "")),
            str(item.get("cor", "")),
            str(item.get("mfi", "")),
            str(item.get("teor_cinzas", "")),
            str(item.get("densidade", "")),
            str(item.get("umidade", "")),
            str(item.get("teste_filme", "")),
        ]
        for item in (itens_qualidade or [])
    ]

    _add_table(pdf, headers, rows, col_widths)

    # Rodape de aprovacao
    pdf.ln(10)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(
        0, 7,
        "Material aprovado para uso conforme especificacoes acima.",
        align="C", new_x="LMARGIN", new_y="NEXT",
    )

    # Assinatura do responsavel tecnico
    pdf.ln(20)
    line_width = 80
    x_center = (pdf.w - line_width) / 2
    y_sig = pdf.get_y()

    pdf.line(x_center, y_sig, x_center + line_width, y_sig)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(x_center, y_sig + 2)
    pdf.cell(line_width, 5, "Responsavel Tecnico", align="C")

    return _to_bytes(pdf)


# ---------------------------------------------------------------------------
# 7. Laudo de Rastreabilidade
# ---------------------------------------------------------------------------

def gerar_pdf_laudo_rastreabilidade(romaneio: dict, itens_rastreio: list[dict]) -> bytes:
    pdf = _create_pdf()
    _header(pdf, "LAUDO DE RASTREABILIDADE")

    numero = romaneio.get("numero_romaneio", romaneio.get("numero_pedido", ""))
    cliente = romaneio.get("cliente", "")
    data_doc = romaneio.get("data", "")

    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, f"Referente ao Romaneio {numero} - Cliente: {cliente}",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 7, f"Data: {data_doc}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    pdf.set_font("Helvetica", "", 9)
    pdf.cell(0, 5, "Este documento certifica a rastreabilidade completa dos lotes enviados,",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "desde a origem da materia-prima ate o produto final.",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)

    headers = ["Lote", "Peso (kg)", "OPE", "Origem", "OPL", "NFs de MP", "Grade", "Cor"]
    col_w = [24, 18, 18, 18, 18, 38, 22, 18]
    rows = []
    for item in (itens_rastreio or []):
        nfs = item.get("nfs_mp", "")
        if isinstance(nfs, list):
            nfs = ", ".join(nfs)
        rows.append([
            str(item.get("codigo_lote", "")),
            str(item.get("peso_kg", "")),
            str(item.get("ope", "")),
            str(item.get("origem", "")),
            str(item.get("opl", "")),
            str(nfs),
            str(item.get("grade", "")),
            str(item.get("cor", "")),
        ])
    _add_table(pdf, headers, rows, col_w)

    pdf.ln(6)
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 7, "Cadeia de rastreabilidade certificada pela Resiban - Resinas Bandeirante LTDA.",
             align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 7, "Material 100% pos-consumo reciclado (PCR).",
             align="C", new_x="LMARGIN", new_y="NEXT")

    y_remaining = pdf.h - 20 - pdf.get_y()
    if y_remaining < 25:
        pdf.add_page()
    pdf.ln(max(10, y_remaining - 15))

    line_width = 70
    gap = (pdf.w - pdf.l_margin - pdf.r_margin - 2 * line_width) / 3
    y_sig = pdf.get_y()
    pdf.set_font("Helvetica", "", 9)
    x1 = pdf.l_margin + gap
    pdf.line(x1, y_sig, x1 + line_width, y_sig)
    pdf.set_xy(x1, y_sig + 2)
    pdf.cell(line_width, 5, "Responsavel Tecnico", align="C")
    x2 = x1 + line_width + gap
    pdf.line(x2, y_sig, x2 + line_width, y_sig)
    pdf.set_xy(x2, y_sig + 2)
    pdf.cell(line_width, 5, "Direcao", align="C")

    return _to_bytes(pdf)
