from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill


HEADER_FILL = PatternFill(start_color="64A624", end_color="64A624", fill_type="solid")
HEADER_FONT = Font(bold=True, color="000000")

# Formato correcto de dólares para Excel
MONEY_FORMAT = '$#,##0.00;[Red]($#,##0.00)'


def export_endorsements_to_excel(endorsements, filename):
    print(f"🔹 Exportando a Excel en '{filename}' ...")

    wb = Workbook()
    ws = wb.active
    ws.title = "Endorsements"

    headers = [
        "Endorsement Effective Date",
        "Endorsement Amount",
        "Endorsement Type",
        "MGA",
        "Policy",
        "Insured",
        "Agents",
        "CSRs",
        "Agency Commission",
        "Agent Commission",
    ]

    ws.append(headers)

    # ---- Estilo headers ----
    for col in range(1, len(headers) + 1):
        cell = ws.cell(row=1, column=col)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(
            horizontal="center",
            vertical="center",
            wrap_text=True  # 👈 permitir que el header use 2 líneas si hace falta
        )

    ws.row_dimensions[1].height = 32  # 👈 header más alto

    current_row = 2

    # ---- Contenido ----
    for e in endorsements:
        endorsement_type_raw = e.get("endorsement_type") or ""
        endorsement_type = endorsement_type_raw.lower()
        is_cancel = "cancel" in endorsement_type

        amount = safe_money(e.get("endorsement_amount"))
        if is_cancel and amount > 0:
            amount = -amount

        row_idx = current_row

        ws.cell(row=row_idx, column=1, value=_format_date(e.get("endorsement_effective")))
        ws.cell(row=row_idx, column=2, value=amount)
        ws.cell(row=row_idx, column=3, value=endorsement_type_raw)
        ws.cell(row=row_idx, column=4, value=e.get("mga"))
        ws.cell(row=row_idx, column=5, value=e.get("policy_number"))
        ws.cell(row=row_idx, column=6, value=e.get("insured"))
        ws.cell(row=row_idx, column=7, value=e.get("agents"))
        ws.cell(row=row_idx, column=8, value=e.get("csrs"))
        ws.cell(row=row_idx, column=9, value=safe_money(e.get("agency_commission")))
        ws.cell(row=row_idx, column=10, value=safe_money(e.get("agent_commission")))

        # ---- Formato dinero ----
        ws.cell(row=row_idx, column=2).number_format = MONEY_FORMAT
        ws.cell(row=row_idx, column=9).number_format = MONEY_FORMAT
        ws.cell(row=row_idx, column=10).number_format = MONEY_FORMAT

        # ---- Si es cancel: monto en rojo ----
        if is_cancel:
            ws.cell(row=row_idx, column=2).font = Font(color="FF0000")

        # ---- Estilo filas: altura fija y SIN wrap ----
        ws.row_dimensions[row_idx].height = 18

        for col in range(1, 11):
            ws.cell(row=row_idx, column=col).alignment = Alignment(
                vertical="center",
                wrap_text=False
            )

        current_row += 1

    # ---- Ancho de columnas fijo (compacto) ----
    widths = {
        "A": 16,  # Date
        "B": 18,  # Amount
        "C": 26,  # Type
        "D": 30,  # MGA
        "E": 18,  # Policy
        "F": 32,  # Insured
        "G": 26,  # Agents
        "H": 26,  # CSRs
        "I": 20,  # Agency Comm
        "J": 20,  # Agent Comm
    }

    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    # Congelar header
    ws.freeze_panes = "A2"

    wb.save(filename)
    print(f"✅ Excel generado: {filename}")


# -----------------------
# Helpers
# -----------------------

def _format_date(value):
    if not value:
        return None
    try:
        return value.split("T")[0]
    except:
        return value


def safe_money(value):
    try:
        if value is None:
            return 0.0
        return float(value)
    except:
        return 0.0
