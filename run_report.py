"""
Script principal para generar el reporte de endorsements con comisiones.
Archivo final se guarda en la carpeta 'output/'.
"""

import os
from app.api.client import NowCertsClient
from app.services.endorsement_report_service import generate_unified_endorsements
from app.exports.excel_reporter import export_endorsements_to_excel

def main():
    # 1️⃣ Inicializar cliente NowCerts (token se toma desde settings.py)
    client = NowCertsClient()  # ✅ No hace falta pasar access_token manualmente

    # 2️⃣ Generar lista unificada de endorsements con comisiones
    print("🔹 Generando lista unificada de endorsements...")
    unified_endorsements = generate_unified_endorsements(client)
    print(f"✅ Se unificaron {len(unified_endorsements)} endorsements.")

    # 3️⃣ Definir ruta de salida dentro de 'output/'
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)  # Crear carpeta si no existe
    output_file = os.path.join(output_dir, "endorsements_report.xlsx")

    # 4️⃣ Exportar a Excel
    print(f"🔹 Exportando a Excel en '{output_file}' ...")
    export_endorsements_to_excel(unified_endorsements, filename=output_file)
    print("🎉 Reporte generado correctamente.")

if __name__ == "__main__":
    main()
