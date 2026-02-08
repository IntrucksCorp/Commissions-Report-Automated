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
    # Request base con retry automático
    # ---------------------------------------------------------
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        max_retries: int = 3
    ) -> Dict[str, Any]:

        url = f"{self.BASE_URL}{endpoint}"

        print(f"🌐 GET {url}")
        if params:
            print(f"   Params: {params}")

        for attempt in range(max_retries):
            try:
                response = self.session.get(
                    url,
                    params=params,
                    timeout=REQUEST_TIMEOUT
                )

                # Manejo de rate limit con retry automático
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        wait_time = 60  # Esperar 1 minuto
                        print(f"⏳ Rate limit alcanzado. Esperando {wait_time}s antes de reintentar... (intento {attempt + 1}/{max_retries})")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise RuntimeError(
                            "🚨 Rate limit alcanzado después de múltiples intentos. "
                            "Intenta de nuevo más tarde."
                        )

                response.raise_for_status()
                return response.json()

            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = 5
                    print(f"⚠️ Error en request: {e}. Reintentando en {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    raise

        raise RuntimeError("No se pudo completar el request después de múltiples intentos")

    # ---------------------------------------------------------
    # Paginación NowCerts con rate limit control mejorado
    # ---------------------------------------------------------
    def get_all_paginated(
        self,
        endpoint: str,
        *,
        top: int = 500,
        skip_start: int = 0,
        orderby: Optional[str] = None,
        max_pages: Optional[int] = None,
        sleep_seconds: float = 0.7  # ⬆️ Aumentado de 0.1 a 0.7 segundos
    ) -> List[Dict[str, Any]]:
        """
        Descarga todos los registros de un endpoint paginado de NowCerts.

        Usa:
            $top
            $skip
            $orderby
            
        Rate limit: 100 requests/min = ~0.6s por request
        Usamos 0.7s para estar seguros
        """

        all_items: List[Dict[str, Any]] = []
        skip = skip_start
        page = 0
        request_count = 0
        start_time = time.time()

        while True:
            params: Dict[str, Any] = {
                "$top": top,
                "$skip": skip,
            }

            if orderby:
                params["$orderby"] = orderby

            # Control de rate limit: asegurar que no hacemos más de 100 req/min
            request_count += 1
            if request_count >= 95:  # Margen de seguridad (95 en vez de 100)
                elapsed = time.time() - start_time
                if elapsed < 60:
                    wait_time = 60 - elapsed + 1  # +1 segundo de margen
                    print(f"⏳ Llegando al límite de rate (95 requests). Esperando {wait_time:.1f}s...")
                    time.sleep(wait_time)
                # Reset contador
                request_count = 0
                start_time = time.time()

            data = self.get(endpoint, params=params)

            # NowCerts devuelve directamente lista o { value: [...] }
            if isinstance(data, dict) and "value" in data:
                items = data["value"]
            else:
                items = data

            print(f"📦 Página {page + 1}: {len(items)} registros (total: {len(all_items) + len(items)})")

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

            # Sleep entre páginas
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