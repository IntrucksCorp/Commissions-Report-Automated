from app.api.policies import get_policies_map


def generate_unified_endorsements(client):
    print("🔹 Generando lista unificada de endorsements...")

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

    print(f"📄 Endorsements: {len(endorsements)}")
    print(f"🏢 Agency Commissions: {len(agency_comms)}")
    print(f"👤 Agent Commissions: {len(agent_comms)}")

    # 2. Indexar comisiones por endorsementDatabaseId
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

    # 3. Unificar todo
    unified = []

    for e in endorsements:
        policy_id = e.get("policyId")
        endorsement_id = e.get("databaseId")

        policy_data = policies_map.get(policy_id, {})

        record = {
            # --- Policy info ---
            "policy_id": policy_id,
            "policy_number": policy_data.get("policy_number"),
            "mga": policy_data.get("mga"),
            "insured": policy_data.get("insured"),
            "agents": policy_data.get("agents"),
            "csrs": policy_data.get("csrs"),

            # --- Endorsement info ---
            "endorsement_id": endorsement_id,
            "endorsement_type": e.get("endorsementTypeText"),
            "endorsement_effective": e.get("date"),
            "endorsement_amount": e.get("amount"),
            "endorsement_status": e.get("statusText"),
            "endorsement_premium_type": e.get("endorsementPremiumTypeText"),
            "create_date": e.get("createDate"),
            "change_date": e.get("changeDate"),

            # --- Commissions raw ---
            "agency_commissions": agency_by_endorsement.get(endorsement_id, []),
            "agent_commissions": agents_by_endorsement.get(endorsement_id, []),
        }

        unified.append(record)

    print(f"✅ Se unificaron {len(unified)} endorsements.")

    return unified
