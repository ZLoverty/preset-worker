import unittest
from unittest.mock import patch

from preset_worker.services import enrichment
from preset_worker.services.enrichment import FeishuClient


class FeishuAuthTests(unittest.TestCase):
    def test_invalid_token_refreshes_and_retries_request(self):
        client = object.__new__(FeishuClient)
        client.app_id = "app-id"
        client.app_secret = "app-secret"
        client.token = "expired-token"
        client._token_refresh_at = 10**30
        calls = []

        def fake_api(url, token, *, method="GET", payload=None):
            calls.append((url, token, method, payload))
            if url == enrichment.AUTH_URL:
                return {"tenant_access_token": "fresh-token", "expire": 7200}
            if token == "expired-token":
                raise RuntimeError("飞书 API 错误 99991663: Invalid access token")
            return {"code": 0, "data": {"ok": True}}

        with patch.object(enrichment, "_api_json", side_effect=fake_api):
            result = client._request_json("https://example.test/records")

        self.assertEqual(result["data"]["ok"], True)
        self.assertEqual([call[1] for call in calls], ["expired-token", "", "fresh-token"])

    def test_expired_token_is_refreshed_before_request(self):
        client = object.__new__(FeishuClient)
        client.app_id = "app-id"
        client.app_secret = "app-secret"
        client.token = "old-token"
        client._token_refresh_at = 0
        calls = []

        def fake_api(url, token, *, method="GET", payload=None):
            calls.append((url, token))
            if url == enrichment.AUTH_URL:
                return {"tenant_access_token": "fresh-token", "expire": 7200}
            return {"code": 0, "data": {}}

        with patch.object(enrichment, "_api_json", side_effect=fake_api):
            client._request_json("https://example.test/records")

        self.assertEqual([call[1] for call in calls], ["", "fresh-token"])


if __name__ == "__main__":
    unittest.main()
