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


def export_endorsements_to_excel(endorsements, filename, date_from="2025-12-01", date_to=None):
    """
    Exporta endorsements a Excel con 2 hojas:
    1. Endorsement Detail (Detalle completo)
    2. Agent Summary (Resumen por agente)
    """
    print(f"🔹 Exportando a Excel en '{filename}' ...")

    # Convertir a lista para permitir múltiples iteraciones (evita que el generador se agote)
    endorsements_list = list(endorsements)

    # 1. Extraer mes y año del período
    try:
        date_obj = datetime.strptime(date_from, "%Y-%m-%d")
        month_name = date_obj.strftime("%B")
        year = date_obj.strftime("%Y")
    except:
        month_name = "N/A"
        year = "N/A"

    # 2. Crear Workbook
    wb = Workbook()

    # --- Hoja 1: Endorsement Detail (Ahora es la PRIMERA) ---
    ws_detail = wb.active
    ws_detail.title = "Endorsement Detail"
    
    # Metadata Detail
    metadata = [
        ["REPORTE DE DETALLE DE ENDORSEMENTS"],
        [f"Fecha Desde:", date_from or "N/A"],
        [f"Fecha Hasta:", date_to or "Hoy"],
        [f"Generado el:", datetime.now().strftime("%Y-%m-%d %H:%M:%S")],
        []
    ]
    for row in metadata:
        ws_detail.append(row)
    
    ws_detail["A1"].font = Font(bold=True, size=14)

    # Headers Detail
    headers_detail = [
        "Endorsement ID", "Endorsement Date", "Endorsement Amount",
        "Endorsement Type", "MGA", "Policy Number",
        "Policy Effective", "Policy Expiration", "Insured",
        "Agent/CSR", "Agency Commission", "Agent Commission"
    ]
    ws_detail.append(headers_detail)
    header_row_detail = len(metadata) + 1

    for col_idx, header in enumerate(headers_detail, 1):
        cell = ws_detail.cell(row=header_row_detail, column=col_idx)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = THIN_BORDER
    ws_detail.row_dimensions[header_row_detail].height = 35

    # Contenido Detail
    detail_count = 0
    detail_total_agent_comm = 0
    
    for e in endorsements_list:
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

        ws_detail.append([
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

        detail_total_agent_comm += agent_comm
        detail_count += 1
        curr_row = ws_detail.max_row

        for col_idx in range(1, 13):
            cell = ws_detail.cell(row=curr_row, column=col_idx)
            cell.font = NORMAL_FONT
            cell.border = THIN_BORDER
            cell.alignment = Alignment(vertical="center", wrap_text=False)

            if col_idx in [3, 11, 12]:
                cell.number_format = MONEY_FORMAT
                if (col_idx == 3 and amount < 0) or (col_idx == 11 and agency_comm < 0) or (col_idx == 12 and agent_comm < 0):
                    cell.font = Font(name="Arial", size=10, color="FF0000")

        ws_detail.row_dimensions[curr_row].height = 20

    # Column Widths Detail
    detail_widths = [36, 16, 18, 26, 32, 20, 15, 15, 30, 30, 18, 18]
    for i, w in enumerate(detail_widths, 1):
        ws_detail.column_dimensions[chr(64 + i)].width = w

    ws_detail.freeze_panes = "A" + str(header_row_detail + 1)
    ws_detail.auto_filter.ref = f"A{header_row_detail}:L{ws_detail.max_row}"

    print(f"💾 Hoja 'Endorsement Detail' creada: {detail_count} filas")

    # --- Hoja 2: Agent Summary (Ahora es la SEGUNDA) ---
    ws_summary = wb.create_sheet("Agent Summary")
    
    # Procesar datos para resumen por agente
    agent_summary_dict = {}
    
    for e in endorsements_list:
        agent = e.get("agent")
        if not agent:
            continue
        
        agent_comm = safe_money(e.get("agent_commission"))
        
        # Detectar si es cancelación para el signo
        endorsement_type_raw = e.get("endorsement_type") or ""
        if "cancel" in endorsement_type_raw.lower() and agent_comm > 0:
             agent_comm = -agent_comm
        elif "cancel" in endorsement_type_raw.lower():
             agent_comm = -abs(agent_comm) if agent_comm != 0 else 0

        if agent not in agent_summary_dict:
            agent_summary_dict[agent] = {
                "count": 0,
                "total_agent_comm": 0.0
            }
        
        agent_summary_dict[agent]["count"] += 1
        agent_summary_dict[agent]["total_agent_comm"] += agent_comm

    # Filtrar agentes con comisión != 0 y ordenar
    filtered_agents = []
    for agent, data in agent_summary_dict.items():
        if abs(data["total_agent_comm"]) > 0.001:
            filtered_agents.append({
                "agent": agent,
                "count": data["count"],
                "total": data["total_agent_comm"]
            })

    # Ordenar: Total DESC, luego Agent ASC
    filtered_agents.sort(key=lambda x: (-x["total"], x["agent"]))

    summary_headers = ["Agent/CSR", "Month", "Year", "Total Endorsements", "Total Agent Commission"]
    ws_summary.append(summary_headers)
    
    # Formato Headers Summary
    for col_idx, header in enumerate(summary_headers, 1):
        cell = ws_summary.cell(row=1, column=col_idx)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        cell.border = THIN_BORDER
    ws_summary.row_dimensions[1].height = 35

    # Datos Summary
    row_idx = 2
    summary_total_count = 0
    summary_total_comm = 0
    
    for agent_data in filtered_agents:
        ws_summary.append([
            agent_data["agent"],
            month_name,
            year,
            agent_data["count"],
            agent_data["total"]
        ])
        
        # Estilos celdas
        for col_idx in range(1, 6):
            cell = ws_summary.cell(row=row_idx, column=col_idx)
            cell.font = NORMAL_FONT
            cell.border = THIN_BORDER
            
            if col_idx == 1: cell.alignment = Alignment(horizontal="left", vertical="center")
            elif col_idx in [2, 3, 4]: cell.alignment = Alignment(horizontal="center", vertical="center")
            elif col_idx == 5:
                cell.alignment = Alignment(horizontal="right", vertical="center")
                cell.number_format = MONEY_FORMAT
                if agent_data["total"] < 0:
                     cell.font = Font(name="Arial", size=10, color="FF0000")
        
        summary_total_count += agent_data["count"]
        summary_total_comm += agent_data["total"]
        ws_summary.row_dimensions[row_idx].height = 20
        row_idx += 1

    # Fila de Totales Summary
    ws_summary.append(["TOTAL", "", "", summary_total_count, summary_total_comm])
    last_row_summary = ws_summary.max_row
    
    TOTAL_FILL = PatternFill(start_color="E8E8E8", end_color="E8E8E8", fill_type="solid")
    DOUBLE_BORDER_TOP = Border(
        top=Side(style='double', color='000000'),
        left=Side(style='thin', color='CCCCCC'),
        right=Side(style='thin', color='CCCCCC'),
        bottom=Side(style='thin', color='CCCCCC')
    )
    
    for col_idx in range(1, 6):
        cell = ws_summary.cell(row=last_row_summary, column=col_idx)
        cell.font = Font(bold=True, name="Arial", size=10)
        cell.fill = TOTAL_FILL
        cell.border = DOUBLE_BORDER_TOP
        if col_idx == 4: cell.alignment = Alignment(horizontal="center", vertical="center")
        if col_idx == 5:
            cell.alignment = Alignment(horizontal="right", vertical="center")
            cell.number_format = MONEY_FORMAT
            if summary_total_comm < 0:
                 cell.font = Font(bold=True, name="Arial", size=10, color="FF0000")

    # Column Widths Summary
    summary_widths = [30, 15, 10, 18, 22]
    for i, w in enumerate(summary_widths, 1):
        ws_summary.column_dimensions[chr(64 + i)].width = w

    ws_summary.freeze_panes = "B2"
    ws_summary.auto_filter.ref = f"A1:E{last_row_summary-1}"

    print(f"💾 Hoja 'Agent Summary' creada: {len(filtered_agents)} agentes para {month_name} {year}")

    # 4. Validar Totales
    assert abs(summary_total_comm - detail_total_agent_comm) < 0.01, f"Error: Totales no coinciden. Summary: {summary_total_comm}, Detail: {detail_total_agent_comm}"
    print("✅ Totales validados correctamente")

    # 5. Guardar
    wb.save(filename)
    print(f"✅ Excel generado: {filename} (Total: {detail_count} filas)")


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
