from datetime import datetime
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.cell import WriteOnlyCell


# Colores profesionales
HEADER_FILL = PatternFill(start_color="2E5C8A",
                          end_color="2E5C8A", fill_type="solid")
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
NORMAL_FONT = Font(name="Arial", size=10)

# Formato de dinero
MONEY_FORMAT = '$#,##0.00;[Red]($#,##0.00)'

# Bordes
THIN_BORDER = Border(
    left=Side(style='thin', color='CCCCCC'),
    right=Side(style='thin', color='CCCCCC'),
    top=Side(style='thin', color='CCCCCC'),
    bottom=Side(style='thin', color='CCCCCC')
)


def export_endorsements_to_excel(endorsements, filename, date_from=None, date_to=None):
    """
    Exporta endorsements a Excel con formato profesional.
    Optimizado usando ws.append() para mayor velocidad sin los riesgos de stream XML de write_only.
    """
    print(f"🔹 Exportando a Excel (Optimized Mode) en '{filename}' ...")

    wb = Workbook()
    ws = wb.active
    ws.title = "Endorsements Report"

    # ---- Metadata ----
    metadata = [
        ["REPORTE DE COMISIONES - NOWCERTS"],
        [f"Fecha Desde:", date_from or "N/A"],
        [f"Fecha Hasta:", date_to or "Hoy"],
        [f"Generado el:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        []  # Fila vacía
    ]
    for row in metadata:
        ws.append(row)

    # Estilo título
    ws["A1"].font = Font(bold=True, size=14)

    # ---- Headers ----
    headers = [
        "Endorsement ID", "Endorsement Date", "Endorsement Amount",
        "Endorsement Type", "MGA", "Policy Number",
        "Policy Effective", "Policy Expiration", "Insured",
        "Agent/CSR", "Agency Commission", "Agent Commission"
    ]

    ws.append(headers)
    header_row_idx = len(metadata) + 1

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=header_row_idx, column=col_idx)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(
            horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER

    ws.row_dimensions[header_row_idx].height = 35

    # ---- Contenido ----
    count = 0
    for e in endorsements:
        endorsement_type_raw = e.get("endorsement_type") or ""
        is_cancel = "cancel" in endorsement_type_raw.lower()

        amount = safe_money(e.get("endorsement_amount"))
        if is_cancel and amount > 0:
            amount = -amount

        agency_comm = safe_money(e.get("agency_commission"))
        agent_comm = safe_money(e.get("agent_commission"))

        if is_cancel:
            agency_comm = -abs(agency_comm) if agency_comm != 0 else 0
            agent_comm = -abs(agent_comm) if agent_comm != 0 else 0

        # Escribir fila usando append
        ws.append([
            e.get("endorsement_id"),
            _format_date(e.get("endorsement_effective")),
            amount,
            endorsement_type_raw,
            e.get("mga"),
            e.get("policy_number"),
            _format_date(e.get("policy_effective_date")),
            _format_date(e.get("policy_expiration_date")),
            e.get("insured"),
            e.get("agent"),
            agency_comm,
            agent_comm
        ])

        count += 1
        current_row = ws.max_row

        # Aplicar estilos a la fila recién agregada
        for col_idx in range(1, 13):
            cell = ws.cell(row=current_row, column=col_idx)
            cell.font = NORMAL_FONT
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=False)

            # Formato dinero (columnas 3, 11, 12)
            if col_idx in [3, 11, 12]:
                cell.number_format = MONEY_FORMAT
                if is_cancel:
                    cell.font = Font(name="Arial", size=10, color="FF0000")

        ws.row_dimensions[current_row].height = 20

        if count % 100 == 0:
            print(f"   ... procesadas {count} filas")

    # ---- Ancho de columnas ----
    widths = [36, 16, 18, 26, 32, 20, 15, 15, 30, 30, 18, 18]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + i)].width = w

    # Congelar y Autofiltro
    # Congelar desde la fila abajo de los headers para que estos siempre sean visibles
    # "A" + str(header_row_idx + 1) congela las filas 1 hasta header_row_idx
    ws.freeze_panes = "A" + str(header_row_idx + 1)

    # El filtro debe empezar en la fila de los headers
    first_col = "A"
    last_col = chr(64 + len(headers))
    ws.auto_filter.ref = f"{first_col}{header_row_idx}:{last_col}{ws.max_row}"

    wb.save(filename)
    print(f"✅ Excel generado: {filename} (Total: {count} filas)")


# -----------------------
# Helpers
# -----------------------

def _format_date(value):
    """Formatea fechas ISO a formato MM/DD/YYYY."""
    if not value:
        return None
    try:
        # Si viene como "2025-12-13T00:00:00" o "2025-12-13"
        date_str = str(value).split("T")[0]
        # Separar año-mes-día
        parts = date_str.split("-")
        if len(parts) == 3:
            year, month, day = parts
            return f"{month}/{day}/{year}"
        return value
    except:
        return value


def safe_money(value):
    """Convierte valores a float de forma segura."""
    try:
        if value is None:
            return 0.0
        return float(value)
    except:
        return 0.0
