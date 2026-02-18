import time
import requests
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("NowCertsClient")


class NowCertsClient:
    """
    Cliente para la API de NowCerts con autenticación automática.
    """

    def __init__(self, base_url: str = settings.NOWCERTS_API_BASE_URL, username: str = settings.NOWCERTS_USERNAME, password: str = settings.NOWCERTS_PASSWORD, timeout: int = settings.REQUEST_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.timeout = timeout
        self.agency_id = settings.NOWCERTS_AGENCY_ID  # Keep existing agency_id

        self.session = requests.Session()
        self.token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None

        # Intentar cargar token manual desde entorno (omite login)
        manual_token = os.getenv("NOWCERTS_ACCESS_TOKEN")
        if manual_token:
            self.token = manual_token
            # Set a very long expiry for manual token
            self.token_expiry = datetime.now() + timedelta(days=365)
            logger.info("🔑 Usando access_token manual desde el entorno.")
            self.session.headers.update({
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json"
            })
        else:
            logger.info("🔄 No hay token manual, se usará login automático.")

    def _login(self) -> str:
        """
        Realiza el login para obtener un access_token con reintentos.
        """
        # La URL correcta suele ser /api/Token
        login_url = f"{self.base_url}/Token"

        payload = {
            "grant_type": "password",
            "username": self.username,
            "password": self.password
        }

        max_retries = 3
        for attempt in range(max_retries):
            logger.info(
                f"🔄 [{attempt+1}/{max_retries}] Intentando login en {login_url}...")
            try:
                # Usamos requests directamente para el login (sin headers de auth)
                response = requests.post(
                    login_url,
                    data=payload,
                    timeout=self.timeout
                )

                if response.status_code == 200:
                    data = response.json()
                    self.token = data.get("access_token")
                    expires_in = data.get("expires_in", 3600)

                    # Guardar expiración con un margen de 5 minutos
                    self.token_expiry = datetime.now() + timedelta(seconds=expires_in - 300)

                    # Actualizar headers de la sesión para subsiguientes llamadas
                    self.session.headers.update({
                        "Authorization": f"Bearer {self.token}",
                        "Content-Type": "application/json"
                    })

                    logger.info(
                        f"✅ Login exitoso para {self.username}. Token de acceso actualizado.")
                    return self.token
                else:
                    logger.error(
                        f"❌ Error en login ({response.status_code}): {response.text}")
                    if response.status_code == 400:  # Credenciales incorrectas usualmente
                        raise ValueError(
                            f"Credenciales de NowCerts inválidas: {response.text}")

                    if attempt < max_retries - 1:
                        time.sleep(5)
                        continue
                    raise RuntimeError(
                        f"Falla en autenticación NowCerts tras varios intentos: {response.status_code}")

            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout) as e:
                wait_time = (attempt + 1) * 10
                logger.warning(
                    f"🕒 Timeout durante el login ({e}). Reintentando en {wait_time}s...")
                if attempt < max_retries - 1:
                    time.sleep(wait_time)
                    continue
                raise
            except Exception as e:
                logger.error(
                    f"🚨 Excepción inesperada durante el login: {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
                raise

        raise RuntimeError(
            "No se pudo realizar el login después de los reintentos.")

    def get_token(self) -> str:
        """
        Retorna el token actual, haciendo login si es necesario.
        """
        if not self.token or not self.token_expiry or datetime.now() >= self.token_expiry:
            # Only attempt login if username/password are provided
            if self.username and self.password:
                return self._login()
            else:
                raise ValueError(
                    "No se proporcionaron credenciales (username/password) para el login automático y no hay un token manual.")
        return self.token

    def request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Realiza una petición a la API manejando auth, rate limits y timeouts.
        """
        self.get_token()

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Eliminar headers manuales que puedan interferir con la sesión
        if "headers" in kwargs:
            kwargs["headers"].pop("Authorization", None)

        max_retries = 3
        for attempt in range(max_retries):  # Intento original + reintentos
            try:
                logger.info(f"🌐 {method} a NowCerts: {endpoint}")
                response = self.session.request(
                    method,
                    url,
                    timeout=self.timeout,
                    **kwargs
                )

                # Manejo de expiración inesperada (401)
                if response.status_code == 401:
                    logger.warning(
                        f"⚠️ Token expirado o inválido (401) en {endpoint}. Renovando...")
                    self._login()
                    continue

                # Manejo de Rate Limit (429)
                if response.status_code == 429:
                    wait_time = 60
                    logger.warning(
                        f"⏳ Rate limit alcanzado en {endpoint}. Esperando {wait_time}s...")
                    time.sleep(wait_time)
                    # Reintento recursivo
                    return self.request(method, endpoint, **kwargs)

                if response.status_code == 400:
                    logger.error(
                        f"❌ Error 400 (Bad Request) en {endpoint}: {response.text}")
                    # No reintentamos un 400 ya que suele ser error de sintaxis
                    response.raise_for_status()

                response.raise_for_status()
                return response.json()

            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectTimeout) as e:
                wait_time = (attempt + 1) * 7
                logger.warning(
                    f"🕒 Timeout en {endpoint} ({e}). Reintentando {attempt + 1}/{max_retries} en {wait_time}s...")
                time.sleep(wait_time)
                continue
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    wait_time = (attempt + 1) * 2
                    logger.warning(
                        f"⚠️ Error de red en {endpoint} ({e}). Reintentando {attempt + 1}/{max_retries} en {wait_time}s...")
                    time.sleep(wait_time)
                    continue
                raise

        raise RuntimeError(
            f"No se pudo completar la petición a {endpoint} después de {max_retries} intentos.")

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Helper para GET requests.
        """
        return self.request("GET", endpoint, params=params)

    def get_all_paginated(
        self,
        endpoint: str,
        *,
        top: int = settings.DEFAULT_TOP,
        skip_start: int = 0,
        orderby: Optional[str] = None,
        select: Optional[str] = None,
        filter: Optional[str] = None,
        max_pages: Optional[int] = None,
        sleep_seconds: float = 0.5
    ) -> List[Dict[str, Any]]:
        """
        Descarga todos los registros y los retorna como una lista.
        (Mantiene compatibilidad con código existente).
        """
        return list(self.yield_all_paginated(
            endpoint,
            top=top,
            skip_start=skip_start,
            orderby=orderby,
            select=select,
            filter=filter,
            max_pages=max_pages,
            sleep_seconds=sleep_seconds
        ))

    def yield_all_paginated(
        self,
        endpoint: str,
        *,
        top: int = settings.DEFAULT_TOP,
        skip_start: int = 0,
        orderby: Optional[str] = None,
        select: Optional[str] = None,
        filter: Optional[str] = None,
        max_pages: Optional[int] = None,
        sleep_seconds: float = 0.5,
        save_snapshot: bool = False
    ):
        """
        Generador que descarga registros de un endpoint paginado de NowCerts.
        Permite procesar datos sin cargar todo en memoria.
        """
        skip = skip_start
        page = 0
        total_yielded = 0

        logger.info(
            f"🚀 Iniciando descarga paginada (stream) de '{endpoint}' (top={top}, skip={skip_start})")
        if filter:
            logger.info(f"   $filter: {filter}")

        all_items_for_snapshot = [] if save_snapshot else None

        while True:
            params: Dict[str, Any] = {
                "$top": top,
                "$skip": skip,
            }

            if orderby:
                params["$orderby"] = orderby
            if select:
                params["$select"] = select
            if filter:
                params["$filter"] = filter

            # Control de rate limit amigable
            if page > 0 and sleep_seconds > 0:
                time.sleep(sleep_seconds)

            data = self.get(endpoint, params=params)

            if isinstance(data, dict) and "value" in data:
                items = data["value"]
            else:
                items = data

            if not items:
                break

            for item in items:
                yield item
                total_yielded += 1

            logger.info(
                f"📦 [{endpoint}] Página {page + 1}: {len(items)} registros (total: {total_yielded})")

            if save_snapshot:
                all_items_for_snapshot.extend(items)

            if len(items) < top:
                break

            skip += top
            page += 1

            if max_pages and page >= max_pages:
                logger.info("🧪 Límite de páginas alcanzado (modo test)")
                break

        logger.info(f"✅ Total descargado (stream): {total_yielded} registros")

        if save_snapshot and all_items_for_snapshot:
            self._save_snapshot(endpoint, all_items_for_snapshot)

    def _save_snapshot(self, endpoint, all_items):
        try:
            os.makedirs("data_raw", exist_ok=True)
            safe_name = endpoint.strip("/").replace("/", "_")
            path = os.path.join("data_raw", f"{safe_name}.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(all_items, f, indent=2, ensure_ascii=False)
            logger.info(f"💾 Snapshot guardado en: {path}")
        except Exception as e:
            logger.warning(
                f"⚠️ No se pudo guardar snapshot de {endpoint}: {e}")
