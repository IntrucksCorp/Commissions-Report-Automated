from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side


# Colores profesionales
HEADER_FILL = PatternFill(start_color="2E5C8A", end_color="2E5C8A", fill_type="solid")
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


def export_endorsements_to_excel(endorsements, filename):
    """
    Exporta endorsements a Excel con formato simplificado.
    - Sin columnas extra de Agent Name / Agent Commission ID
    - 1 agente y 1 CSR por fila
    - Solo endorsements con comisiones
    """
    print(f"🔹 Exportando a Excel en '{filename}' ...")

    wb = Workbook()
    ws = wb.active
    ws.title = "Endorsements Report"

    # Headers simplificados
    headers = [
        "Endorsement ID",
        "Endorsement Date",
        "Endorsement Amount",
        "Endorsement Type",
        "MGA",
        "Policy Number",
        "Policy Effective",
        "Policy Expiration",
        "Insured",
        "Agents",  # 1 agente por fila
        "CSRs",    # 1 CSR por fila
        "Agency Commission",
        "Agent Commission",
        "Total Commission",
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
            wrap_text=True
        )
        cell.border = THIN_BORDER

    ws.row_dimensions[1].height = 35

    current_row = 2

    # ---- Contenido ----
    for e in endorsements:
        endorsement_type_raw = e.get("endorsement_type") or ""
        endorsement_type = endorsement_type_raw.lower()
        is_cancel = "cancel" in endorsement_type

        amount = safe_money(e.get("endorsement_amount"))
        if is_cancel and amount > 0:
            amount = -amount
        
        agency_comm = safe_money(e.get("agency_commission"))
        agent_comm = safe_money(e.get("agent_commission"))
        
        # Si es cancel, las comisiones también en negativo
        if is_cancel:
            if agency_comm > 0:
                agency_comm = -agency_comm
            if agent_comm > 0:
                agent_comm = -agent_comm
        
        total_comm = agency_comm + agent_comm

        row_idx = current_row

        # Escribir datos
        ws.cell(row=row_idx, column=1, value=e.get("endorsement_id"))
        ws.cell(row=row_idx, column=2, value=_format_date(e.get("endorsement_effective")))
        ws.cell(row=row_idx, column=3, value=amount)
        ws.cell(row=row_idx, column=4, value=endorsement_type_raw)
        ws.cell(row=row_idx, column=5, value=e.get("mga"))
        ws.cell(row=row_idx, column=6, value=e.get("policy_number"))
        ws.cell(row=row_idx, column=7, value=_format_date(e.get("policy_effective_date")))
        ws.cell(row=row_idx, column=8, value=_format_date(e.get("policy_expiration_date")))
        ws.cell(row=row_idx, column=9, value=e.get("insured"))
        ws.cell(row=row_idx, column=10, value=e.get("agents"))  # 1 agente
        ws.cell(row=row_idx, column=11, value=e.get("csrs"))    # 1 CSR
        ws.cell(row=row_idx, column=12, value=agency_comm)
        ws.cell(row=row_idx, column=13, value=agent_comm)
        ws.cell(row=row_idx, column=14, value=total_comm)
        
        # Formato dinero
        ws.cell(row=row_idx, column=3).number_format = MONEY_FORMAT
        ws.cell(row=row_idx, column=12).number_format = MONEY_FORMAT
        ws.cell(row=row_idx, column=13).number_format = MONEY_FORMAT
        ws.cell(row=row_idx, column=14).number_format = MONEY_FORMAT
        
        # Si es cancel: valores en rojo
        if is_cancel:
            ws.cell(row=row_idx, column=3).font = Font(name="Arial", size=10, color="FF0000")
            ws.cell(row=row_idx, column=12).font = Font(name="Arial", size=10, color="FF0000")
            ws.cell(row=row_idx, column=13).font = Font(name="Arial", size=10, color="FF0000")
            ws.cell(row=row_idx, column=14).font = Font(name="Arial", size=10, color="FF0000")

        # Font y bordes
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=row_idx, column=col)
            cell.font = NORMAL_FONT
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=False)

        ws.row_dimensions[row_idx].height = 20

        current_row += 1

    # ---- Ancho de columnas ----
    widths = {
        "A": 36,  # Endorsement ID
        "B": 16,  # Date
        "C": 18,  # Amount
        "D": 26,  # Type
        "E": 32,  # MGA
        "F": 20,  # Policy
        "G": 15,  # Effective
        "H": 15,  # Expiration
        "I": 30,  # Insured
        "J": 28,  # Agents (1 solo)
        "K": 28,  # CSRs (1 solo)
        "L": 18,  # Agency Comm
        "M": 18,  # Agent Comm
        "N": 18,  # Total Comm
    }

    for col, width in widths.items():
        ws.column_dimensions[col].width = width

    # Congelar header y primera columna
    ws.freeze_panes = "B2"
    
    # Agregar autofiltros
    ws.auto_filter.ref = ws.dimensions
    print("✅ Autofiltros agregados a todas las columnas")

    wb.save(filename)
    print(f"✅ Excel generado: {filename}")
    print(f"   Total de filas: {current_row - 1:,}")


# -----------------------
# Helpers
# -----------------------

def _format_date(value):
    """Formatea fechas ISO a formato corto."""
    if not value:
        return None
    try:
        return value.split("T")[0]
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