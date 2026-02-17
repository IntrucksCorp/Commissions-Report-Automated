from app.services.validators import validate_date_range, get_today_utc_str
from datetime import timedelta


def test_range():
    print(f"Hoy UTC: {get_today_utc_str()}")

    # Test valid range
    s_dt, e_dt = validate_date_range("2025-12-01", "2026-02-16")
    print(f"Start: {s_dt}")
    print(f"End: {e_dt}")
    limit = e_dt + timedelta(days=1)
    print(f"Limit (exclusive): {limit}")

    # Test invalid range
    try:
        validate_date_range("2026-02-16", "2025-12-01")
    except ValueError as e:
        print(f"Error esperado (rango invertido): {e}")


if __name__ == "__main__":
    test_range()
