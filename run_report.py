"""
Script principal para generar el reporte de comisiones.

VERSIÓN CON FILTRO DE FECHAS:
- Solo endorsements desde 12/01/2025 hasta hoy
- 1 fila por agente de cada endorsement
- Lista completa de agentes de la póliza
- Solo endorsements con comisiones > 0
"""

import os
from datetime import datetime
from app.services.nowcerts_client import NowCertsClient
from app.services.endorsement_report_service import generate_unified_endorsements
from app.exports.excel_reporter import export_endorsements_to_excel


def main(date_from="2025-12-01"):
    """
    Genera el reporte de comisiones con filtro de fecha.

    Args:
        date_from: Fecha inicial en formato "YYYY-MM-DD" (default: 2025-12-01)
    """
    print("=" * 80)
    print("GENERADOR DE REPORTE DE COMISIONES - CON FILTRO DE FECHAS")
    print("=" * 80)
    print()
    print(
        f"📅 Período: desde {date_from} hasta {datetime.now().strftime('%Y-%m-%d')}")
    print()
    print("📋 Características:")
    print("   - 1 fila por agente de cada endorsement")
    print("   - Solo endorsements con comisiones")
    print("   - Lista completa de agentes de la póliza")
    print()

    # 1️⃣ Inicializar cliente
    print("🔹 Inicializando cliente NowCerts...")
    client = NowCertsClient()
    print()

    # 2️⃣ Generar reporte
    print("🔹 Generando reporte con detalle por agente...")
    unified_endorsements = generate_unified_endorsements(
        client, date_from=date_from)

    # Contar endorsements únicos
    unique_endorsements = len(set(e.get('endorsement_id')
                              for e in unified_endorsements))
    print()
    print(f"✅ Reporte generado:")
    print(f"   Total de filas: {len(unified_endorsements):,}")
    print(f"   Endorsements únicos: {unique_endorsements:,}")
    print(
        f"   Promedio de filas por endorsement: {len(unified_endorsements)/unique_endorsements:.1f}")
    print()

    # 3️⃣ Definir ruta de salida
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    output_file = os.path.join(
        output_dir, f"endorsements_commission_report_{date_from.replace('-', '')}_to_today.xlsx")

    # 4️⃣ Exportar a Excel
    print(f"🔹 Exportando a Excel...")
    export_endorsements_to_excel(unified_endorsements, filename=output_file)

    print()
    print("=" * 80)
    print("🎉 REPORTE GENERADO CORRECTAMENTE")
    print("=" * 80)
    print(f"📄 Archivo: {output_file}")
    print()
    print("📊 Estructura:")
    print("   ✅ Solo endorsements desde", date_from)
    print("   ✅ 1 fila por agente")
    print("   ✅ Agents: lista completa de la póliza")
    print("   ✅ Agency Commission: repetida por agente")
    print("   ✅ Agent Commission: individual por agente")
    print()


if __name__ == "__main__":
    # 🔥 CONFIGURACIÓN DE FECHA 🔥

    # Opción 1: Desde 12/01/2025 (default)
    main(date_from="2025-12-01")

    # Opción 2: Cambiar la fecha de inicio
    # main(date_from="2025-11-01")  # Desde noviembre
    # main(date_from="2026-01-01")  # Desde enero 2026
    # main(date_from="2026-02-01")  # Desde febrero 2026
