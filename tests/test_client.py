from app.api.client import NowCertsClient

def main():
    client = NowCertsClient()

    # Prueba simple: GET a un endpoint real
    data = client.get(
        "/AgentList",
        params={
            "$top": 10,
            "$skip": 0,
            "$orderby": "changeDate desc"
        }
    )

    print("Tipo:", type(data))
    print("Claves:", data.keys())
    print("Primer registro:", data.get("value", [])[:1])


if __name__ == "__main__":
    main()
