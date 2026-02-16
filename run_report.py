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
from app.services.validators import get_today_utc_str, validate_date_range


def main(date_from="2025-12-01", date_to=None):
    """
    Script principal para generar el reporte de comisiones.
    """
    if date_to is None:
        date_to = get_today_utc_str()

    print("=" * 80)
    print("GENERADOR DE REPORTE DE COMISIONES - CON RANGO DE FECHAS")
    print("=" * 80)
    print(f"\n📅 Período: desde {date_from} hasta {date_to}")

    try:
        # Validar el rango antes de empezar
        validate_date_range(date_from, date_to)
    except ValueError as e:
        print(f"❌ Error en fechas: {e}")
        return

    # 1. Inicializar cliente
    print("\n🔹 Inicializando cliente NowCerts...")
    client = NowCertsClient()

    # 2. Generar datos (pasa el rango)
    unified_endorsements = generate_unified_endorsements(
        client, date_from=date_from, date_to=date_to)

    if not unified_endorsements:
        print("⚠️ No hay datos para el reporte en este período.")
        return

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

    # 3. Exportar a Excel (pasa el rango para metadata)
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"endorsements_commission_report_{date_from.replace('-', '')}_to_{date_to.replace('-', '')}.xlsx"
    filepath = os.path.join(output_dir, filename)

    print(f"\n🔹 Exportando a Excel...")
    export_endorsements_to_excel(
        unified_endorsements, filepath, date_from, date_to)

    print("\n" + "=" * 80)
    print("🎉 REPORTE GENERADO CORRECTAMENTE")
    print("=" * 80)
    print(f"📄 Archivo: {filepath}")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    # Soporte básico para argumentos CLI
    # Uso: python run_report.py [date_from] [date_to]
    d_from = sys.argv[1] if len(sys.argv) > 1 else "2025-12-01"
    d_to = sys.argv[2] if len(sys.argv) > 2 else None

    main(date_from=d_from, date_to=d_to)

    # Opción 1: Desde 12/01/2025 (default)
    # main(date_from="2025-12-01")

    # Opción 2: Cambiar la fecha de inicio
    # main(date_from="2025-11-01")  # Desde noviembre
    # main(date_from="2026-01-01")  # Desde enero 2026
    # main(date_from="2026-02-01")  # Desde febrero 2026
