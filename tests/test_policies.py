from app.api.client import NowCertsClient
from app.api.policies import get_policies_map


def main():
    client = NowCertsClient()

    policies_map = get_policies_map(client)

    print(f"\n📊 Total policies in map: {len(policies_map)}\n")

    # Mostrar 3 ejemplos
    i = 0
    for policy_id, data in policies_map.items():
        print("🧾 Policy ID:", policy_id)
        for k, v in data.items():
            print(f"   {k}: {v}")
        print("-" * 60)

        i += 1
        if i >= 3:
            break


if __name__ == "__main__":
    main()
