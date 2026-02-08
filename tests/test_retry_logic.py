import unittest
from unittest.mock import MagicMock, patch
from app.api.client import NowCertsClient
import time


class TestNowCertsClientRetry(unittest.TestCase):
    @patch("app.api.client.requests.Session")
    @patch("app.api.client.time.sleep", return_value=None)  # No esperar en tests
    def test_get_retry_on_429(self, mock_sleep, mock_session_class):
        # Configurar el mock de la sesión
        mock_session = mock_session_class.return_value

        # Simular: primer llamado 429, segundo llamado 200
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429

        mock_response_200 = MagicMock()
        mock_response_200.status_code = 200
        mock_response_200.json.return_value = {"success": True}

        mock_session.get.side_effect = [mock_response_429, mock_response_200]

        client = NowCertsClient()
        result = client.get("/test-endpoint", base_delay=0.1)

        self.assertEqual(result, {"success": True})
        self.assertEqual(mock_session.get.call_count, 2)
        mock_sleep.assert_called_once_with(0.1)

    @patch("app.api.client.requests.Session")
    @patch("app.api.client.time.sleep", return_value=None)
    def test_get_max_retries_exceeded(self, mock_sleep, mock_session_class):
        mock_session = mock_session_class.return_value

        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429

        # Simular 6 fallos (1 intento original + 5 reintentos)
        mock_session.get.return_value = mock_response_429

        client = NowCertsClient()
        with self.assertRaises(RuntimeError) as cm:
            client.get("/test-endpoint", max_retries=5, base_delay=0.1)

        self.assertIn(
            "Rate limit persistente después de 5 reintentos", str(cm.exception)
        )
        self.assertEqual(mock_session.get.call_count, 6)


if __name__ == "__main__":
    unittest.main()
