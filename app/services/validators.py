from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple


def validate_date_format(date_str: str) -> bool:
    """
    Valida que el string tenga formato YYYY-MM-DD.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except (ValueError, TypeError):
        return False


def parse_date(date_str: str) -> datetime:
    """
    Convierte un string YYYY-MM-DD a objeto datetime (medianoche UTC).
    """
    return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def validate_date_range(start_date_str: str, end_date_str: str) -> Tuple[datetime, datetime]:
    """
    Valida formato y rango de fechas.
    Retorna la tupla (start_dt, end_dt) en UTC.
    Lanza ValueError si falla.
    """
    if not validate_date_format(start_date_str):
        raise ValueError(
            f"Formato de fecha inicial inválido: {start_date_str}. Use YYYY-MM-DD.")

    if not validate_date_format(end_date_str):
        raise ValueError(
            f"Formato de fecha final inválido: {end_date_str}. Use YYYY-MM-DD.")

    start_dt = parse_date(start_date_str)
    end_dt = parse_date(end_date_str)

    if end_dt < start_dt:
        raise ValueError(
            f"La fecha final ({end_date_str}) no puede ser anterior a la inicial ({start_date_str}).")

    return start_dt, end_dt


def get_today_utc_str() -> str:
    """
    Retorna la fecha de hoy en UTC como string YYYY-MM-DD.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")
