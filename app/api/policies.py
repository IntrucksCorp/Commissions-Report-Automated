from typing import Dict


def get_policies_map(client) -> Dict[str, dict]:
    """
    Obtiene todas las pólizas desde /PolicyList y construye un mapa:

    {
        policyId: {
            policy_number,
            mga,
            insured,
            agents,
            csrs
        }
    }
    """

    print("🔹 Descargando pólizas desde /PolicyList ...")

    policies = client.get_all_paginated(
        endpoint="/PolicyList",
        orderby="changeDate desc",
        top=500
    )

    print(f"✅ Se descargaron {len(policies)} pólizas.")

    policies_map = {}

    for p in policies:
        # Construir Agents
        agents_list = p.get("agents", [])
        agents = ", ".join(
            f"{a.get('firstName', '').strip()} {a.get('lastName', '').strip()}".strip()
            for a in agents_list
        )

        # Construir CSRs
        csrs_list = p.get("csRs", [])
        csrs = ", ".join(
            f"{c.get('firstName', '').strip()} {c.get('lastName', '').strip()}".strip()
            for c in csrs_list
        )

        policies_map[p["databaseId"]] = {
            "policy_number": p.get("number"),
            "mga": p.get("mgaName"),
            "insured": p.get("insuredCommercialName"),
            "agents": agents,
            "csrs": csrs,
            "effective_date": p.get("effectiveDate"),
            "expiration_date": p.get("expirationDate"),
        }

    print("✅ Mapa de pólizas construido correctamente.")

    return policies_map
