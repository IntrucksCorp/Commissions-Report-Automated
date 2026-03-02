"""
Script principal para generar el reporte de comisiones.

VERSIÓN CON FILTRO DE FECHAS Y AGENTE:
- Filtro por rango de fechas
- Filtro opcional por agente
- 1 fila por agente de cada endorsement
- Solo endorsements con comisiones > 0
"""

import os
from datetime import datetime
from app.services.nowcerts_client import NowCertsClient
from app.services.endorsement_report_service import generate_unified_endorsements
from app.exports.excel_reporter import export_endorsements_to_excel
from app.services.validators import get_today_utc_str, validate_date_range


def main(date_from="2025-12-01", date_to=None, agent=None):
    """
    Script principal para generar el reporte de comisiones.
    
    Args:
        date_from: Fecha inicial (YYYY-MM-DD)
        date_to: Fecha final (YYYY-MM-DD), opcional
        agent: Nombre del agente para filtrar (ej: "JOSE GIRALDO"), opcional
    """
    if date_to is None:
        date_to = get_today_utc_str()

    print("=" * 80)
    print("GENERADOR DE REPORTE DE COMISIONES")
    print("=" * 80)
    print(f"\n📅 Período: desde {date_from} hasta {date_to}")
    if agent:
        print(f"👤 Filtro de agente: {agent}")

    try:
        # Validar el rango antes de empezar
        validate_date_range(date_from, date_to)
    except ValueError as e:
        print(f"❌ Error en fechas: {e}")
        return

    # 1. Inicializar cliente
    print("\n🔹 Inicializando cliente NowCerts...")
    client = NowCertsClient()

    # 2. Generar datos con filtro de agente
    unified_endorsements = list(generate_unified_endorsements(
        client, 
        date_from=date_from, 
        date_to=date_to,
        agent_filter=agent  # ← NUEVO PARÁMETRO
    ))

    if not unified_endorsements:
        print("⚠️ No hay datos para el reporte en este período.")
        return

    # Contar endorsements únicos
    unique_endorsements = len(set(e.get('endorsement_id') for e in unified_endorsements))
    print()
    print(f"✅ Reporte generado:")
    print(f"   Total de filas: {len(unified_endorsements):,}")
    print(f"   Endorsements únicos: {unique_endorsements:,}")
    print(f"   Promedio de filas por endorsement: {len(unified_endorsements)/unique_endorsements:.1f}")
    print()

    # 3. Exportar a Excel
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # 🧹 Limpiar archivos antiguos en output/
    import glob
    old_files = glob.glob(os.path.join(output_dir, "*.xlsx"))
    for f in old_files:
        try:
            os.remove(f)
        except Exception as e:
            print(f"⚠️ No se pudo eliminar {f}: {e}")

    # Nombre incluye agente si está filtrado
    agent_suffix = f"_{agent.replace(' ', '_')}" if agent else ""
    filename = f"reporte_comisiones_{date_from}_{date_to}{agent_suffix}.xlsx"
    filepath = os.path.join(output_dir, filename)

    print(f"\n🔹 Exportando a Excel...")
    export_endorsements_to_excel(unified_endorsements, filepath, date_from, date_to)

    print("\n" + "=" * 80)
    print("🎉 REPORTE GENERADO CORRECTAMENTE")
    print("=" * 80)
    print(f"📄 Archivo: {filepath}")
    print("=" * 80)


if __name__ == "__main__":
    import sys

    # Soporte para argumentos CLI
    # Uso: python run_report.py [date_from] [date_to] [agent]
    d_from = sys.argv[1] if len(sys.argv) > 1 else "2025-12-01"
    d_to = sys.argv[2] if len(sys.argv) > 2 else None
    agent_name = sys.argv[3] if len(sys.argv) > 3 else None

    main(date_from=d_from, date_to=d_to, agent=agent_name)

    # Ejemplos de uso:
    # python run_report.py 2025-12-01
    # python run_report.py 2025-12-01 2026-02-28
    # python run_report.py 2025-12-01 2026-02-28 "JOSE GIRALDO"