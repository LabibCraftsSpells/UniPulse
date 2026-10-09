"""
Tests for authentication error states and API failure handling (Section 14.10 & 14.12).
"""

import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app


class TestOAuthAndAPIErrorHandling(unittest.TestCase):
    """Test OAuth and API failure modes produce clear HTTP error states."""

    def setUp(self):
        self.client = TestClient(app, base_url="http://localhost:8000")

    def test_unauthenticated_request_returns_401(self):
        """Unauthenticated requests to protected endpoints return 401."""
        response = self.client.get("/api/emails")
        self.assertEqual(response.status_code, 401)
        self.assertIn("Not authenticated", response.json().get("detail", ""))

    def test_unauthenticated_tasks_returns_401(self):
        response = self.client.get("/api/tasks")
        self.assertEqual(response.status_code, 401)

    def test_unauthenticated_briefing_returns_401(self):
        response = self.client.get("/api/briefing")
        self.assertEqual(response.status_code, 401)

    def test_health_check_returns_200(self):
        """Public health check returns 200."""
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_oauth_callback_invalid_state_returns_400(self):
        """Invalid CSRF state in OAuth callback returns 400 Bad Request."""
        response = self.client.get("/auth/google/callback?state=bad_state&code=test_code")
        self.assertEqual(response.status_code, 400)
        self.assertIn("state", response.json().get("detail", "").lower())


if __name__ == "__main__":
    unittest.main()
