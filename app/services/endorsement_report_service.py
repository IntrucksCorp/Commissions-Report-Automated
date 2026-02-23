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
    seen_endorsements = set()
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

        endorsement_id = e.get("databaseId")
        if not endorsement_id:
            continue

        # --- DE-DUPLICACIÓN ---
        if endorsement_id in seen_endorsements:
            # print(f"⚠️ Endorsement duplicado detectado ({endorsement_id}). Saltando...")
            continue
        seen_endorsements.add(endorsement_id)

        policy_id = e.get("policyId")
        policy_data = policies_map.get(policy_id, {})

        # Obtener comisiones indexadas
        e_agency_comms = agency_by_endorsement.get(endorsement_id, [])
        e_agent_comms = agents_by_endorsement.get(endorsement_id, [])

        endorsement_amount = e.get("amount", 0)

        # Determinar si hay algún "Agency Fee" (Fixed Value en Agencia)
        has_fixed_agency_comm = any(c.get("commissionTypeText") == "Fixed Value" for c in e_agency_comms)
        original_type = e.get("endorsementTypeText") or ""
        
        # Calcular comisión de agencia (soporta Fixed y Percent)
        agency_commission_total = calculate_agency_commission(
            e_agency_comms, endorsement_amount)
        
        # --- NUEVO: Si el tipo de endorsement es "Agency Fee", el monto mismo es la comisión ---
        is_agency_fee_type = "Agency Fee" in original_type
        if is_agency_fee_type and agency_commission_total == 0:
            agency_commission_total = endorsement_amount
            
        # Si tiene un cobro fijo o es de tipo Agency Fee, lo etiquetamos como "Agency Fee"
        display_type = "Agency Fee" if (has_fixed_agency_comm or is_agency_fee_type) else original_type

        # PRE-FILTRO: Calcular total de comisiones de agentes
        # Si AMBAS comisiones son 0, saltar
        total_agent_comm = sum(
            calculate_agent_commission_value(
                ac, endorsement_amount, agency_commission_total)
            for ac in e_agent_comms
        )

        if agency_commission_total == 0 and total_agent_comm == 0:
            continue

        # Si hay comisiones de agentes asociadas, procesarlas individualmente
        if e_agent_comms:
            for agent_comm in e_agent_comms:
                agent_name = agent_comm.get("agentName", "").strip()
                if not agent_name:
                    continue

                agent_val = calculate_agent_commission_value(
                    agent_comm, endorsement_amount, agency_commission_total
                )

                # Para Agency Fee, permitimos incluso si el valor del agente es 0
                # (aunque para otros tipos el filtro de 0-0 se mantiene arriba)
                if not is_agency_fee_type and agency_commission_total == 0 and agent_val == 0:
                    continue

                record = create_record(
                    e, policy_data, endorsement_id, policy_id,
                    agent_name, agency_commission_total, agent_val,
                    display_type=display_type
                )
                yield record
                count_yielded += 1
        else:
            # Sin agent commissions, usar agentes de la póliza
            # Esto es vital para las Agency Fees que vienen como endorsements sin comisiones de agentes
            agents_raw = policy_data.get("agents", "")
            agents_list = [a.strip() for a in agents_raw.split(
                ",") if a.strip()] if agents_raw else []

            if not agents_list:
                # Si no hay agentes en la póliza, generamos una fila vacía para capturar la comisión
                if agency_commission_total > 0:
                    yield create_record(
                        e, policy_data, endorsement_id, policy_id,
                        "", agency_commission_total, 0,
                        display_type=display_type
                    )
                    count_yielded += 1
                continue

            for agent_name in agents_list:
                # Emitimos una fila por cada agente con el total de la agencia
                yield create_record(
                    e, policy_data, endorsement_id, policy_id,
                    agent_name, agency_commission_total, 0,
                    display_type=display_type
                )
                count_yielded += 1

    print(
        f"✅ Proceso de generación finalizado. Total filas enviadas: {count_yielded}")


def calculate_agent_commission_value(agent_comm, endorsement_amount, agency_commission_total):
    """Calcula el valor de comisión de un agente individual."""
    commission_val = agent_comm.get("commissionValue")
    commission_type = agent_comm.get("commissionTypeText", "Percent")
    payment_type = agent_comm.get("policyCommissionAgentPaymentTypeText", "")

    if commission_val is None:
        return 0

    try:
        val = float(commission_val)
        if commission_type == "Fixed Value":
            return val
        
        if "From Agency Commission" in payment_type:
            return agency_commission_total * (val / 100.0)
        else:
            return endorsement_amount * (val / 100.0)
    except (ValueError, TypeError):
        return 0


def create_record(e, policy_data, endorsement_id, policy_id, agent_individual, agency_comm, agent_comm, display_type=None):
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
        "endorsement_type": display_type or e.get("endorsementTypeText"),
        "endorsement_effective": e.get("date"),
        "endorsement_amount": e.get("amount"),
        "endorsement_status": e.get("statusText"),

        # --- Commissions ---
        "agency_commission": agency_comm,
        "agent_commission": agent_comm,
    }
