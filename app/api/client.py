import time
import requests
import os
import json
from typing import Dict, Any, List, Optional

from config.settings import (
    NOWCERTS_API_BASE_URL,
    NOWCERTS_ACCESS_TOKEN,
    REQUEST_TIMEOUT,
)


class NowCertsClient:
    BASE_URL = NOWCERTS_API_BASE_URL

    def __init__(self):
        self.session = requests.Session()

        if not NOWCERTS_ACCESS_TOKEN:
            raise ValueError("❌ Falta la variable de entorno NOWCERTS_ACCESS_TOKEN")

        self.session.headers.update({
            "Authorization": f"Bearer {NOWCERTS_ACCESS_TOKEN}",
            "Content-Type": "application/json"
        })

        print("🔐 Cliente inicializado con Access Token manual")

    # ---------------------------------------------------------
    # Request base
    # ---------------------------------------------------------
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:

        url = f"{self.BASE_URL}{endpoint}"

        print(f"🌐 GET {url}")
        if params:
            print(f"   Params: {params}")

        response = self.session.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        # Manejo explícito de rate limit
        if response.status_code == 429:
            raise RuntimeError(
                "🚨 Rate limit alcanzado (100 requests/min). "
                "Reduce paginación o usa $top=500."
            )

        response.raise_for_status()
        return response.json()

    # ---------------------------------------------------------
    # Paginación NowCerts
    # ---------------------------------------------------------
    def get_all_paginated(
        self,
        endpoint: str,
        *,
        top: int = 500,
        skip_start: int = 0,
        orderby: Optional[str] = None,
        max_pages: Optional[int] = None,
        sleep_seconds: float = 0.1
    ) -> List[Dict[str, Any]]:
        """
        Descarga todos los registros de un endpoint paginado de NowCerts.

        Usa:
            $top
            $skip
            $orderby
        """

        all_items: List[Dict[str, Any]] = []
        skip = skip_start
        page = 0

        while True:
            params: Dict[str, Any] = {
                "$top": top,
                "$skip": skip,
            }

            if orderby:
                params["$orderby"] = orderby

            data = self.get(endpoint, params=params)

            # NowCerts devuelve directamente lista o { value: [...] }
            if isinstance(data, dict) and "value" in data:
                items = data["value"]
            else:
                items = data

            print(f"📦 Página {page + 1}: {len(items)} registros")

            if not items:
                break

            all_items.extend(items)

            # Última página
            if len(items) < top:
                break

            skip += top
            page += 1

            # Límite artificial (modo test)
            if max_pages and page >= max_pages:
                print("🧪 Límite de páginas alcanzado (modo test)")
                break

            if sleep_seconds > 0:
                time.sleep(sleep_seconds)

        print(f"✅ Total descargado: {len(all_items)} registros")

        # -----------------------------
        # Guardar snapshot en data_raw
        # -----------------------------
        try:
            os.makedirs("data_raw", exist_ok=True)

            safe_name = endpoint.strip("/").replace("/", "_")
            path = os.path.join("data_raw", f"{safe_name}.json")

            with open(path, "w", encoding="utf-8") as f:
                json.dump(all_items, f, indent=2, ensure_ascii=False)

            print(f"💾 Snapshot guardado en: {path}")

        except Exception as e:
            print(f"⚠️ No se pudo guardar snapshot de {endpoint}: {e}")

        return all_items
