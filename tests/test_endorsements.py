from app.api.client import NowCertsClient

def test_policy_endorsement_detail_list(client: NowCertsClient):
    print("\n📄 Probando PolicyEndorsementDetailList")

    data = client.get(
        "/PolicyEndorsementDetailList",
        params={
            "$top": 10,
            "$skip": 0,
            "$orderby": "changeDate desc"
        }
    )

    print("✔ Registros:", len(data.get("value", [])))
    if data.get("value"):
        print("✔ Ejemplo:", data["value"][0])


def test_policy_endorsement_agents_commission_detail_list(client: NowCertsClient):
    print("\n💰 Probando PolicyEndorsementAgentsCommissionDetailList")

    data = client.get(
        "/PolicyEndorsementAgentsCommissionDetailList",
        params={
            "$top": 10,
            "$skip": 0,
            "$orderby": "changeDate desc"
        }
    )

    print("✔ Registros:", len(data.get("value", [])))
    if data.get("value"):
        print("✔ Ejemplo:", data["value"][0])


def test_policy_endorsement_agency_commission_detail_list(client: NowCertsClient):
    print("\n🏢 Probando PolicyEndorsementAgencyCommissionDetailList")

    data = client.get(
        "/PolicyEndorsementAgencyCommissionDetailList",
        params={
            "$top": 10,
            "$skip": 0,
            "$orderby": "changeDate desc"
        }
    )

    print("✔ Registros:", len(data.get("value", [])))
    if data.get("value"):
        print("✔ Ejemplo:", data["value"][0])


def main():
    client = NowCertsClient()

    test_policy_endorsement_detail_list(client)
    test_policy_endorsement_agents_commission_detail_list(client)
    test_policy_endorsement_agency_commission_detail_list(client)


if __name__ == "__main__":
    main()
