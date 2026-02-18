import os
import glob
import logging
from datetime import datetime
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Dict, Any

from app.services.nowcerts_client import NowCertsClient
from app.services.endorsement_report_service import generate_unified_endorsements
from app.exports.excel_reporter import export_endorsements_to_excel
from app.services.validators import validate_date_format, validate_date_range

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
        ...,
        description="Fecha inicial en formato YYYY-MM-DD (ej: 2025-12-01). Requerido.",
        example="2025-12-01"
    ),
    date_to: str = Query(
        None,
        description="Fecha final en formato YYYY-MM-DD (ej: 2026-02-16). Opcional, por defecto es hoy (UTC).",
        example="2026-02-16"
    ),
    client: NowCertsClient = Depends(get_nowcerts_client)
):
    """
    Genera el reporte de comisiones en formato Excel para un rango de fechas.

    - **date_from**: Fecha obligatoria de inicio.
    - **date_to**: Fecha opcional de fin (inclusive). Si se omite, se usa la fecha actual en UTC.
    """
    if date_to is None:
        date_to = get_today_utc_str()

    logger.info(
        f"📥 Solicitud de generación de reporte: {date_from} hasta {date_to}")

    try:
        # Validación centralizada
        validate_date_range(date_from, date_to)
    except ValueError as e:
        logger.warning(f"⚠️ Validación de fechas fallida: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))

    try:
        # 1. Generar datos del reporte (Generator)
        logger.info(
            f"⏳ Iniciando flujo de datos para el reporte unificado desde {date_from} hasta {date_to}...")
        unified_endorsements = generate_unified_endorsements(
            client, date_from=date_from, date_to=date_to)

        # 2. Guardar en Excel temporalmente (Consumiendo el generador)
        output_dir = "output"
        os.makedirs(output_dir, exist_ok=True)

        # 🧹 Limpiar archivos antiguos en output/
        old_files = glob.glob(os.path.join(output_dir, "*.xlsx"))
        for f in old_files:
            try:
                os.remove(f)
            except Exception as e:
                logger.warning(f"No se pudo eliminar archivo antiguo {f}: {e}")

        filename = f"reporte_comisiones_{date_from}_{date_to}.xlsx"
        filepath = os.path.join(output_dir, filename)

        logger.info(f"💾 Generando y exportando a Excel: {filename} ...")
        export_endorsements_to_excel(
            unified_endorsements, filepath, date_from=date_from, date_to=date_to)

        # 3. Retornar archivo
        return FileResponse(
            path=filepath,
            filename=filename,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        logger.error(f"🚨 Error generando reporte: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error interno generado el reporte: {str(e)}"
        )
