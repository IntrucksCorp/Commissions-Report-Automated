"""
API para trabajar con comisiones de NowCerts.
Incluye comisiones de agencia y de agentes.
"""

def get_agency_commissions(client):
    """
    Trae las comisiones de agencia de todos los endorsements.
    """
    try:
        endpoint = "/PolicyEndorsementAgencyCommissionDetailList"
        agency_comms = client.get_all_paginated(
            endpoint=endpoint,
            orderby="changeDate desc"  # Campo principal para ordenar
        )
        print(f"✅ Comisiones de agencia obtenidas: {len(agency_comms)}")
        return agency_comms
    except Exception as e:
        print(f"❌ Error al obtener comisiones de agencia: {e}")
        return []

def get_agent_commissions(client):
    """
    Trae las comisiones de agentes de todos los endorsements.
    """
    try:
        endpoint = "/PolicyEndorsementAgentsCommissionDetailList"
        agent_comms = client.get_all_paginated(
            endpoint=endpoint,
            orderby="changeDate desc"  # Campo principal para ordenar
        )
        print(f"✅ Comisiones de agentes obtenidas: {len(agent_comms)}")
        return agent_comms
    except Exception as e:
        print(f"❌ Error al obtener comisiones de agentes: {e}")
        return []
