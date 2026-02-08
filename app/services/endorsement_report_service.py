from app.api.policies import get_policies_map
from app.services.commision_calculator import calculate_commissions
from datetime import datetime


def generate_unified_endorsements(client, date_from="2025-12-01"):
    """
    Genera lista de endorsements con detalle por agente.
    
    Args:
        client: Cliente de NowCerts API
        date_from: Fecha inicial en formato "YYYY-MM-DD" (default: 2025-12-01)
    
    Returns:
        Lista de endorsements con 1 fila por agente, filtrados por fecha
    """
    print("🔹 Generando reporte con detalle por agente...")
    print(f"📅 Filtro de fecha: desde {date_from} hasta hoy")

    # 1. Descargar datos base
    policies_map = get_policies_map(client)

    endorsements = client.get_all_paginated(
        endpoint="/PolicyEndorsementDetailList",
        orderby="changeDate desc"
    )

    agency_comms = client.get_all_paginated(
        endpoint="/PolicyEndorsementAgencyCommissionDetailList",
        orderby="changeDate desc"
    )

    agent_comms = client.get_all_paginated(
        endpoint="/PolicyEndorsementAgentsCommissionDetailList",
        orderby="changeDate desc"
    )

    print(f"📄 Endorsements descargados: {len(endorsements)}")
    print(f"🏢 Agency Commissions: {len(agency_comms)}")
    print(f"👤 Agent Commissions: {len(agent_comms)}")

    # 2. Filtrar endorsements por fecha
    date_from_obj = datetime.strptime(date_from, "%Y-%m-%d")
    endorsements_filtered = []
    
    for e in endorsements:
        endorsement_date = e.get("date") or e.get("createDate")
        if not endorsement_date:
            continue
        
        try:
            # Parse fecha (formato: "2025-12-01T00:00:00" o "2025-12-01")
            date_str = endorsement_date.split("T")[0]
            endorsement_date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            
            # Filtrar desde date_from
            if endorsement_date_obj >= date_from_obj:
                endorsements_filtered.append(e)
        except:
            # Si no se puede parsear, incluir el endorsement
            endorsements_filtered.append(e)
    
    print(f"✅ Endorsements después de filtrar por fecha: {len(endorsements_filtered)}")

    # 3. Indexar comisiones por endorsementDatabaseId
    agency_by_endorsement = {}
    for a in agency_comms:
        eid = a.get("endorsementDatabaseId")
        if not eid:
            continue
        agency_by_endorsement.setdefault(eid, []).append(a)

    agents_by_endorsement = {}
    for a in agent_comms:
        eid = a.get("endorsementDatabaseId")
        if not eid:
            continue
        agents_by_endorsement.setdefault(eid, []).append(a)

    # 4. Generar filas
    unified = []

    for e in endorsements_filtered:
        policy_id = e.get("policyId")
        endorsement_id = e.get("databaseId")

        policy_data = policies_map.get(policy_id, {})
        
        # Obtener listas de comisiones
        agency_comms_list = agency_by_endorsement.get(endorsement_id, [])
        agent_comms_list = agents_by_endorsement.get(endorsement_id, [])
        
        endorsement_amount = e.get("amount", 0)
        
        # Calcular comisión de agencia
        from app.services.commision_calculator import calculate_agency_commission
        agency_commission_total = calculate_agency_commission(agency_comms_list, endorsement_amount)
        
        # Solo procesar si hay comisiones de agencia O de agente
        total_agent_comm = sum(
            calculate_agent_commission_value(ac, endorsement_amount, agency_commission_total)
            for ac in agent_comms_list
        )
        
        if agency_commission_total == 0 and total_agent_comm == 0:
            continue
        
        # Obtener lista COMPLETA de agentes de la póliza
        agents_raw = policy_data.get("agents", "")
        agents_list_full = [a.strip() for a in agents_raw.split(",") if a.strip()] if agents_raw else []
        
        # Obtener lista de CSRs
        csrs_raw = policy_data.get("csrs", "")
        csrs_list = [c.strip() for c in csrs_raw.split(",") if c.strip()] if csrs_raw else []
        
        # Crear un mapa de agente -> comisión
        agent_commissions_map = {}
        for agent_comm in agent_comms_list:
            agent_name = agent_comm.get("agentName", "").strip()
            if agent_name:
                agent_commissions_map[agent_name] = calculate_agent_commission_value(
                    agent_comm, endorsement_amount, agency_commission_total
                )
        
        # Si NO hay agentes en agent_comms_list, usar la lista completa de la póliza
        if agent_comms_list:
            # Usar los agentes que tienen comisión configurada
            agents_to_process = [ac.get("agentName", "").strip() for ac in agent_comms_list if ac.get("agentName")]
        else:
            # Usar TODOS los agentes de la póliza
            agents_to_process = agents_list_full
        
        # Si no hay agentes para procesar, crear 1 fila con agency commission
        if not agents_to_process:
            if agency_commission_total > 0:
                record = create_record(
                    e, policy_data, endorsement_id, policy_id,
                    agents_raw, csrs_list[0] if csrs_list else "",
                    agency_commission_total, 0
                )
                unified.append(record)
            continue
        
        # Crear 1 fila por agente
        for idx, agent_name in enumerate(agents_to_process):
            # Obtener comisión de este agente (puede ser 0 si no está configurada)
            agent_commission_value = agent_commissions_map.get(agent_name, 0)
            
            # Asignar 1 CSR a esta fila (distribuir)
            csr_for_this_row = csrs_list[idx % len(csrs_list)] if csrs_list else ""
            
            record = create_record(
                e, policy_data, endorsement_id, policy_id,
                agents_raw,  # Lista completa de agentes
                csr_for_this_row,
                agency_commission_total,
                agent_commission_value
            )
            
            unified.append(record)

    # 5. Ordenar por fecha (más reciente primero)
    unified_sorted = sorted(
        unified,
        key=lambda x: x.get('endorsement_effective') or '1900-01-01',
        reverse=True  # Más reciente primero
    )
    
    print(f"✅ Se generaron {len(unified_sorted)} filas con comisiones.")
    print(f"✅ Ordenadas por fecha (más reciente primero)")

    return unified_sorted


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


def create_record(e, policy_data, endorsement_id, policy_id, agents_full, csr, agency_comm, agent_comm):
    """Crea un registro unificado."""
    return {
        # --- IDs ---
        "endorsement_id": endorsement_id,
        "policy_id": policy_id,
        
        # --- Policy info ---
        "policy_number": policy_data.get("policy_number"),
        "mga": policy_data.get("mga"),
        "insured": policy_data.get("insured"),
        "agents": agents_full,  # Lista COMPLETA de agentes
        "csrs": csr,
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