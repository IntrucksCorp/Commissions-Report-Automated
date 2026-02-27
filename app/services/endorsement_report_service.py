from app.api.policies import get_policies_map
from app.services.commision_calculator import calculate_commissions
from app.services.validators import parse_date, get_today_utc_str, validate_date_range
from datetime import timedelta


def normalize_text_for_search(text):
    """
    Normaliza texto para búsqueda eliminando acentos y convirtiendo a mayúsculas.
    """
    if not text:
        return ""
    
    # Reemplazos de caracteres acentuados
    replacements = {
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U',
        'Ñ': 'N',
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n'
    }
    
    result = str(text).upper().strip()
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    return result


def agent_matches_filter(agent_name, agent_filter):
    """
    Verifica si un nombre de agente coincide con el filtro.
    Soporta múltiples estrategias de matching.
    
    Args:
        agent_name: Nombre completo del agente (ej: "Sara Tobón - Red")
        agent_filter: Filtro aplicado (ej: "Sara Tobón" o "SARA TOBON")
    
    Returns:
        bool: True si hay match, False si no
    """
    if not agent_filter:
        return True
    
    # Normalizar ambos textos
    agent_normalized = normalize_text_for_search(agent_name)
    filter_normalized = normalize_text_for_search(agent_filter)
    
    # Estrategia 1: Match directo en el string completo
    # "SARA TOBON" en "SARA TOBON - RED" ✅
    if filter_normalized in agent_normalized:
        return True
    
    # Estrategia 2: Extraer solo la parte del nombre (antes del guion)
    # "Sara Tobón - Red" -> "SARA TOBON"
    name_part = agent_normalized.split(" - ")[0].strip() if " - " in agent_normalized else agent_normalized
    
    # Match en la parte del nombre
    if filter_normalized in name_part:
        return True
    
    # Match inverso (el nombre está en el filtro)
    if name_part in filter_normalized:
        return True
    
    # Estrategia 3: Match por palabras individuales
    # "SARA TOBON" debe encontrar "SARA TOBON - RED"
    # Cada palabra del filtro debe estar en el nombre
    filter_words = set(filter_normalized.split())
    name_words = set(name_part.split())
    
    if filter_words.issubset(name_words):
        return True
    
    # Estrategia 4: Match flexible (al menos una palabra coincide)
    # Útil para nombres parciales
    if any(word in name_words for word in filter_words if len(word) > 2):
        # Solo si todas las palabras del filtro aparecen
        return filter_words.issubset(name_words)
    
    return False


def generate_unified_endorsements(client, date_from="2025-12-01", date_to=None, agent_filter=None):
    """
    Generador que produce endorsements con detalle por agente.
    Usa filtrado en API y streaming para mayor eficiencia.
    
    Args:
        client: Cliente de NowCerts
        date_from: Fecha inicial (YYYY-MM-DD)
        date_to: Fecha final (YYYY-MM-DD), opcional
        agent_filter: Nombre del agente para filtrar (ej: "SARA TOBON"), opcional
    """
    if date_to is None:
        date_to = get_today_utc_str()

    print(f"🔹 Generando reporte unificado (Streaming) ...")
    print(f"📅 Rango: {date_from} a {date_to}")
    if agent_filter:
        print(f"👤 Filtro de agente: {agent_filter}")

    # 1. Descargar catálogos/lookups
    policies_map = get_policies_map(client)

    odata_filter = f"date ge '{date_from}' and date le '{date_to}'"
    print(f"🔍 Filtro OData: {odata_filter}")

    # Descargar comisiones
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

    # Indexar comisiones
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

    # 2. Descargar Endorsements usando STREAMING
    endorsements_gen = client.yield_all_paginated(
        endpoint="/PolicyEndorsementDetailList",
        orderby="date desc",
        top=2000
    )

    # 3. Procesar y yield
    from app.services.commision_calculator import calculate_agency_commission

    count_yielded = 0
    count_filtered_by_agent = 0
    seen_endorsements = set()
    
    for e in endorsements_gen:
        e_date_full = e.get("date")
        if not e_date_full:
            continue

        e_date = e_date_full[:10]

        # Filtro local por fecha
        if e_date > date_to:
            continue

        if e_date < date_from:
            print(f"⏹️ Fecha límite alcanzada ({e_date}). Finalizando stream.")
            break

        endorsement_id = e.get("databaseId")
        if not endorsement_id:
            continue

        # DE-DUPLICACIÓN
        if endorsement_id in seen_endorsements:
            continue
        seen_endorsements.add(endorsement_id)

        policy_id = e.get("policyId")
        policy_data = policies_map.get(policy_id, {})

        # Obtener comisiones
        e_agency_comms = agency_by_endorsement.get(endorsement_id, [])
        e_agent_comms = agents_by_endorsement.get(endorsement_id, [])

        endorsement_amount = e.get("amount", 0)

        # Determinar tipo
        has_fixed_agency_comm = any(c.get("commissionTypeText") == "Fixed Value" for c in e_agency_comms)
        original_type = e.get("endorsementTypeText") or ""
        
        # Calcular comisión de agencia
        agency_commission_total = calculate_agency_commission(e_agency_comms, endorsement_amount)
        
        is_agency_fee_type = "Agency Fee" in original_type
        if is_agency_fee_type and agency_commission_total == 0:
            agency_commission_total = endorsement_amount
            
        display_type = "Agency Fee" if (has_fixed_agency_comm or is_agency_fee_type) else original_type

        # PRE-FILTRO: Calcular total
        total_agent_comm = sum(
            calculate_agent_commission_value(ac, endorsement_amount, agency_commission_total)
            for ac in e_agent_comms
        )

        if agency_commission_total == 0 and total_agent_comm == 0:
            continue

        # Procesar agentes
        if e_agent_comms:
            for agent_comm in e_agent_comms:
                agent_name = agent_comm.get("agentName", "").strip()
                if not agent_name:
                    continue

                # *** FILTRO POR AGENTE (MEJORADO) ***
                if not agent_matches_filter(agent_name, agent_filter):
                    count_filtered_by_agent += 1
                    continue

                agent_val = calculate_agent_commission_value(
                    agent_comm, endorsement_amount, agency_commission_total
                )

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
            # Sin agent commissions
            agents_raw = policy_data.get("agents", "")
            agents_list = [a.strip() for a in agents_raw.split(",") if a.strip()] if agents_raw else []

            if not agents_list:
                if agency_commission_total > 0:
                    # Si hay filtro activo, saltar filas sin agente
                    if agent_filter:
                        count_filtered_by_agent += 1
                        continue
                        
                    yield create_record(
                        e, policy_data, endorsement_id, policy_id,
                        "", agency_commission_total, 0,
                        display_type=display_type
                    )
                    count_yielded += 1
                continue

            for agent_name in agents_list:
                # *** FILTRO POR AGENTE (MEJORADO) ***
                if not agent_matches_filter(agent_name, agent_filter):
                    count_filtered_by_agent += 1
                    continue
                
                yield create_record(
                    e, policy_data, endorsement_id, policy_id,
                    agent_name, agency_commission_total, 0,
                    display_type=display_type
                )
                count_yielded += 1

    print(f"✅ Proceso finalizado. Filas enviadas: {count_yielded}")
    if agent_filter:
        print(f"🔍 Filas filtradas por agente: {count_filtered_by_agent}")


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
        "endorsement_id": endorsement_id,
        "policy_id": policy_id,
        "policy_number": policy_data.get("policy_number"),
        "mga": policy_data.get("mga"),
        "insured": policy_data.get("insured"),
        "agent": agent_individual,
        "policy_effective_date": policy_data.get("effective_date"),
        "policy_expiration_date": policy_data.get("expiration_date"),
        "endorsement_type": display_type or e.get("endorsementTypeText"),
        "endorsement_effective": e.get("date"),
        "endorsement_amount": e.get("amount"),
        "endorsement_status": e.get("statusText"),
        "agency_commission": agency_comm,
        "agent_commission": agent_comm,
    }