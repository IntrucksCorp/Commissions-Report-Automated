from app.api.policies import get_policies_map
from app.services.commision_calculator import calculate_commissions
from app.services.validators import parse_date, get_today_utc_str, validate_date_range
from datetime import timedelta


def generate_unified_endorsements(client, date_from="2025-12-01", date_to=None):
    """
    Generador que produce endorsements con detalle por agente.
    Usa filtrado en API y streaming para mayor eficiencia.
    """
    if date_to is None:
        date_to = get_today_utc_str()

    print(f"🔹 Generando reporte unificado (Streaming) ...")
    print(f"📅 Rango: {date_from} a {date_to}")

    # 1. Descargar catálogos/lookups (estos sí en memoria)
    policies_map = get_policies_map(client)

    # Construir filtro OData para fechas
    # date ge 'YYYY-MM-DD' and date le 'YYYY-MM-DD'
    odata_filter = f"date ge '{date_from}' and date le '{date_to}'"
    print(f"🔍 Filtro OData: {odata_filter}")

    # Descargar comisiones (lookups) - Usamos top=2000 para rapidez
    print("🔹 Descargando comisiones de agencia...")
    agency_comms_list = client.get_all_paginated(
        endpoint="/PolicyEndorsementAgencyCommissionDetailList",
        orderby="changeDate desc",
        top=2000
    )

    print("🔹 Descargando comisiones de agentes...")
    agent_comms_list = client.get_all_paginated(
        endpoint="/PolicyEndorsementAgentsCommissionDetailList",
        orderby="changeDate desc",
        top=2000
    )

    # Indexar comisiones por endorsementDatabaseId para búsqueda O(1)
    agency_by_endorsement = {}
    for a in agency_comms_list:
        eid = a.get("endorsementDatabaseId")
        if eid:
            agency_by_endorsement.setdefault(eid, []).append(a)

    agents_by_endorsement = {}
    for a in agent_comms_list:
        eid = a.get("endorsementDatabaseId")
        if eid:
            agents_by_endorsement.setdefault(eid, []).append(a)

    # 2. Descargar Endorsements usando STREAMING (Generador)
    # NOTA: Se eliminó el filtro OData ($filter) porque la API retorna 500
    # en este endpoint específico al intentar filtrar por fechas.
    endorsements_gen = client.yield_all_paginated(
        endpoint="/PolicyEndorsementDetailList",
        # filter=odata_filter,  <-- Desactivado por inestabilidad de la API
        orderby="date desc",    # Ordenado desde la API para permitir early-stop
        top=2000
    )

    # 3. Procesar y yield
    from app.services.commision_calculator import calculate_agency_commission

    count_yielded = 0
    for e in endorsements_gen:
        e_date_full = e.get("date")
        if not e_date_full:
            continue

        e_date = e_date_full[:10]  # Formato YYYY-MM-DD

        # Filtro local
        if e_date > date_to:
            continue  # Todavía no llegamos al rango deseado

        if e_date < date_from:
            # Optimizacion: Como vienen en 'date desc', si llegamos a fechas
            # menores que date_from, ya no habrán más registros válidos.
            print(f"⏹️ Fecha límite alcanzada ({e_date}). Finalizando stream.")
            break

        policy_id = e.get("policyId")
        endorsement_id = e.get("databaseId")
        policy_data = policies_map.get(policy_id, {})

        # Obtener comisiones indexadas
        e_agency_comms = agency_by_endorsement.get(endorsement_id, [])
        e_agent_comms = agents_by_endorsement.get(endorsement_id, [])

        endorsement_amount = e.get("amount", 0)

        # Calcular comisión de agencia
        agency_commission_total = calculate_agency_commission(
            e_agency_comms, endorsement_amount)

        # PRE-FILTRO: Calcular total de comisiones de agentes
        # Si AMBAS comisiones son 0, saltar (filtra Taxes, Policy Fees, etc.)
        total_agent_comm = sum(
            calculate_agent_commission_value(
                ac, endorsement_amount, agency_commission_total)
            for ac in e_agent_comms
        )

        if agency_commission_total == 0 and total_agent_comm == 0:
            continue

        # Si hay comisiones de agentes asociadas
        if e_agent_comms:
            for agent_comm in e_agent_comms:
                agent_name = agent_comm.get("agentName", "").strip()
                if not agent_name:
                    continue

                agent_val = calculate_agent_commission_value(
                    agent_comm, endorsement_amount, agency_commission_total
                )

                if agency_commission_total == 0 and agent_val == 0:
                    continue

                record = create_record(
                    e, policy_data, endorsement_id, policy_id,
                    agent_name, agency_commission_total, agent_val
                )
                yield record
                count_yielded += 1
        else:
            # Sin agent commissions, usar agentes de la póliza
            agents_raw = policy_data.get("agents", "")
            agents_list = [a.strip() for a in agents_raw.split(
                ",") if a.strip()] if agents_raw else []

            if not agents_list:
                if agency_commission_total > 0:
                    yield create_record(
                        e, policy_data, endorsement_id, policy_id,
                        "", agency_commission_total, 0
                    )
                    count_yielded += 1
                continue

            for agent_name in agents_list:
                yield create_record(
                    e, policy_data, endorsement_id, policy_id,
                    agent_name, agency_commission_total, 0
                )
                count_yielded += 1

    print(
        f"✅ Proceso de generación finalizado. Total filas enviadas: {count_yielded}")


def calculate_agent_commission_value(agent_comm, endorsement_amount, agency_commission_total):
    """Calcula el valor de comisión de un agente individual."""
    agent_percent = agent_comm.get("commissionValue")
    payment_type = agent_comm.get("policyCommissionAgentPaymentTypeText", "")

    if agent_percent is None:
        return 0

    try:
        percent = float(agent_percent)
        if "From Agency Commission" in payment_type:
            return agency_commission_total * (percent / 100.0)
        else:
            return endorsement_amount * (percent / 100.0)
    except (ValueError, TypeError):
        return 0


def create_record(e, policy_data, endorsement_id, policy_id, agent_individual, agency_comm, agent_comm):
    """Crea un registro unificado."""
    return {
        # --- IDs ---
        "endorsement_id": endorsement_id,
        "policy_id": policy_id,

        # --- Policy info ---
        "policy_number": policy_data.get("policy_number"),
        "mga": policy_data.get("mga"),
        "insured": policy_data.get("insured"),
        "agent": agent_individual,  # Solo el agente individual de esta fila
        "policy_effective_date": policy_data.get("effective_date"),
        "policy_expiration_date": policy_data.get("expiration_date"),

        # --- Endorsement info ---
        "endorsement_type": e.get("endorsementTypeText"),
        "endorsement_effective": e.get("date"),
        "endorsement_amount": e.get("amount"),
        "endorsement_status": e.get("statusText"),

        # --- Commissions ---
        "agency_commission": agency_comm,
        "agent_commission": agent_comm,
    }
