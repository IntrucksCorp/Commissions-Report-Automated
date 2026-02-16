from datetime import datetime


def validate_date_format(date_str: str) -> bool:
    """
    Valida que el string tenga formato YYYY-MM-DD.
    """
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False
