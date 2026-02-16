import os
import logging
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Dict, Any

from app.services.nowcerts_client import NowCertsClient
from app.services.endorsement_report_service import generate_unified_endorsements
from app.exports.excel_reporter import export_endorsements_to_excel
from app.services.validators import validate_date_format

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CommissionsAPI")

app = FastAPI(
    title="Commissions Report API",
    description="API con autenticación automática para NowCerts",
    version="2.0.0"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get NowCertsClient


def get_nowcerts_client():
    """
    Inyecta una instancia de NowCertsClient.
    """
    return NowCertsClient()


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.get("/nowcerts/test")
async def test_nowcerts_connection(
    client: NowCertsClient = Depends(get_nowcerts_client)
):
    """
    Endpoint de prueba para verificar la conexión con NowCerts.
    Intenta obtener el primer carrier de la lista.
    """
    logger.info("Solicitud de prueba de conexión recibida.")
    try:
        # Intentamos obtener un carrier para validar el token
        data = client.get("CarrierList", params={"$top": 1})
        return {
            "status": "success",
            "message": "Conexión con NowCerts exitosa",
            "data": data
        }
    except Exception as e:
        logger.error(f"Error en endpoint de prueba: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al conectar con NowCerts: {str(e)}"
        )


@app.get("/generate-report")
async def generate_report_endpoint(
    date_from: str = Query(
        "2025-12-01", description="Fecha inicial en formato YYYY-MM-DD"),
    client: NowCertsClient = Depends(get_nowcerts_client)
):
    """
    Genera el reporte de comisiones y lo devuelve como un archivo Excel.
    """
    logger.info(
        f"📥 Solicitud de generación de reporte recibida: date_from={date_from}")

    if not validate_date_format(date_from):
        raise HTTPException(
            status_code=400,
            detail="Formato de fecha inválido. Use YYYY-MM-DD."
        )

    try:
        # 1. Generar datos del reporte
        logger.info("⏳ Generando datos del reporte unificado...")
        unified_endorsements = generate_unified_endorsements(
            client, date_from=date_from)

        if not unified_endorsements:
            return {"status": "success", "message": "No se encontraron comisiones para el período indicado.", "data": []}

        # 2. Guardar en Excel temporalmente
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)
        filename = f"report_{date_from}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
        filepath = os.path.join(output_dir, filename)

        logger.info(
            f"💾 Exportando {len(unified_endorsements)} filas a Excel...")
        export_endorsements_to_excel(unified_endorsements, filepath)

        # 3. Retornar archivo
        return FileResponse(
            path=filepath,
            filename=f"endorsements_report_{date_from}.xlsx",
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        logger.error(f"🚨 Error generando reporte: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno generado el reporte: {str(e)}"
        )
