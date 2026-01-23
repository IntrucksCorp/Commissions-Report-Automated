"""
API para trabajar con Endorsements de NowCerts.
"""

def get_all_endorsements(client):
    """
    Trae todos los endorsements desde NowCerts usando get_all_paginated.
    """
    try:
        endpoint = "/PolicyEndorsementDetailList"
        # Ahora pasamos orderby obligatorio
        endorsements = client.get_all_paginated(
            endpoint=endpoint,
            orderby="changeDate desc"  # Campo principal para ordenar
        )
        print(f"✅ Endorsements obtenidos: {len(endorsements)}")
        return endorsements
    except Exception as e:
        print(f"❌ Error al obtener endorsements: {e}")
        return []
