"""Regression checks for Web account bootstrap and shared-data guard."""

import tempfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.middlewares.auth import add_auth_middleware
from api.v1.endpoints.auth import router as auth_router
from api.v1.endpoints import auth as auth_endpoint
from api.v1.endpoints.stocks import router as stocks_router
from api.v1.endpoints.personal_notifications import router as personal_notifications_router
from api.deps import get_system_config_service
from src import auth, web_accounts
from src.storage import WebUser, WebWatchlistItem, WebNotificationChannel, WebScheduledPushTask
from src.services import web_notification_channels


class _AccountDatabase:
    def __init__(self, path: Path):
        self.engine = create_engine(f"sqlite:///{path}")
        WebUser.__table__.create(self.engine)
        WebWatchlistItem.__table__.create(self.engine)
        WebNotificationChannel.__table__.create(self.engine)
        WebScheduledPushTask.__table__.create(self.engine)
        self.session_factory = sessionmaker(bind=self.engine)

    @contextmanager
    def session_scope(self):
        with self.session_factory() as session:
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise


class WebAccountFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        data_dir = Path(self.temp.name)
        database = _AccountDatabase(data_dir / "accounts.db")
        self.addCleanup(database.engine.dispose)
        self.patchers = [
            patch.object(web_accounts, "enabled", return_value=True),
            patch.object(web_accounts.DatabaseManager, "get_instance", return_value=database),
            patch.object(auth, "_get_data_dir", return_value=data_dir),
        ]
        for patcher in self.patchers:
            patcher.start()
            self.addCleanup(patcher.stop)
        auth._session_secret = None
        self.addCleanup(setattr, auth, "_session_secret", None)
        app = FastAPI()
        add_auth_middleware(app)
        app.include_router(auth_router, prefix="/api/v1/auth")
        app.include_router(stocks_router, prefix="/api/v1/stocks")
        app.include_router(personal_notifications_router, prefix="/api/v1/personal/notifications")

        class LegacyConfig:
            def __init__(self):
                self.stock_list = "AAPL"

            def get_config(self, include_schema=False):
                return {"config_version": "v1", "items": [{"key": "STOCK_LIST", "value": self.stock_list}]}

            def update(self, **kwargs):
                self.stock_list = kwargs["items"][0]["value"]

        self.legacy_config = LegacyConfig()
        app.dependency_overrides[get_system_config_service] = lambda: self.legacy_config

        @app.get("/api/v1/private")
        def private():
            return {"ok": True}

        @app.get("/api/v1/system/config")
        def system_config():
            return {"secret": "never for ordinary users"}

        self.client = TestClient(app, client=("127.0.0.1", 12345))

    def test_first_admin_requires_legacy_password_and_ordinary_user_can_use_workbench(self):
        with patch.object(auth_endpoint, "has_stored_password", return_value=True), patch.object(
            auth_endpoint, "verify_stored_password", side_effect=lambda password: password == "old-secret"
        ):
            wrong = self.client.post("/api/v1/auth/register", json={
                "username": "owner", "password": "new-secret-123", "passwordConfirm": "new-secret-123",
                "legacyPassword": "wrong",
            })
            self.assertEqual(wrong.status_code, 403)
            self.assertFalse(web_accounts.has_admin())

            created = self.client.post("/api/v1/auth/register", json={
                "username": "owner", "password": "new-secret-123", "passwordConfirm": "new-secret-123",
                "legacyPassword": "old-secret",
            })
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["role"], "admin")
        status = self.client.get("/api/v1/auth/status").json()
        self.assertTrue(status["loggedIn"])
        self.assertEqual(status["user"]["role"], "admin")
        self.assertEqual(self.client.get("/api/v1/private").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/system/config").status_code, 200)

        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 204)
        self.assertEqual(self.client.get("/api/v1/private").status_code, 401)
        ordinary = self.client.post("/api/v1/auth/register", json={
            "username": "reader", "password": "another-secret", "passwordConfirm": "another-secret",
        })
        self.assertEqual(ordinary.status_code, 201)
        self.assertEqual(ordinary.json()["role"], "user")
        self.assertEqual(self.client.get("/api/v1/private").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/system/config").status_code, 403)
        self.assertEqual(self.client.post("/api/v1/auth/logout").status_code, 204)
        self.assertEqual(self.client.get("/api/v1/private").status_code, 401)
        login = self.client.post("/api/v1/auth/login", json={"username": "reader", "password": "another-secret"})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(self.client.get("/api/v1/private").status_code, 200)

    def test_first_admin_rejects_nonlocal_connection(self):
        async def remote_app(scope, receive, send):
            if scope["type"] == "http":
                scope = {**scope, "client": ("198.51.100.10", 12345)}
            await self.client.app(scope, receive, send)

        with TestClient(remote_app) as remote:
            response = remote.post("/api/v1/auth/register", json={
                "username": "owner", "password": "new-secret-123", "passwordConfirm": "new-secret-123",
            })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(web_accounts.has_admin())

    def test_first_admin_rejects_forwarded_local_connection(self):
        response = self.client.post("/api/v1/auth/register", headers={"X-Forwarded-For": "198.51.100.10"}, json={
            "username": "owner", "password": "new-secret-123", "passwordConfirm": "new-secret-123",
        })
        self.assertEqual(response.status_code, 403)
        self.assertFalse(web_accounts.has_admin())

    def test_watchlists_are_private_and_legacy_stock_list_stays_with_admin(self):
        owner = self.client.post("/api/v1/auth/register", json={
            "username": "owner", "password": "owner-secret", "passwordConfirm": "owner-secret",
        })
        self.assertEqual(owner.status_code, 201)
        self.assertEqual(self.client.get("/api/v1/stocks/watchlist").json()["stock_codes"], ["AAPL"])
        self.client.post("/api/v1/auth/logout")

        first = self.client.post("/api/v1/auth/register", json={
            "username": "reader1", "password": "reader-secret", "passwordConfirm": "reader-secret",
        })
        self.assertEqual(first.status_code, 201)
        self.assertEqual(self.client.get("/api/v1/stocks/watchlist").json()["stock_codes"], [])
        added = self.client.post("/api/v1/stocks/watchlist/add", json={"stock_code": "aapl"})
        self.assertEqual(added.json()["stock_codes"], ["aapl"])
        duplicate = self.client.post("/api/v1/stocks/watchlist/add", json={"stock_code": "AAPL"})
        self.assertEqual(duplicate.json()["stock_codes"], ["aapl"])
        self.assertEqual(self.legacy_config.stock_list, "AAPL")
        self.assertEqual(self.client.get("/api/v1/private").status_code, 200)
        self.client.post("/api/v1/auth/logout")

        second = self.client.post("/api/v1/auth/register", json={
            "username": "reader2", "password": "reader-secret", "passwordConfirm": "reader-secret",
        })
        self.assertEqual(second.status_code, 201)
        self.assertEqual(self.client.get("/api/v1/stocks/watchlist").json()["stock_codes"], [])
        self.assertEqual(self.client.post("/api/v1/stocks/watchlist/remove", json={"stock_code": "AAPL"}).json()["stock_codes"], [])
        self.client.post("/api/v1/auth/logout")

        self.client.post("/api/v1/auth/login", json={"username": "reader1", "password": "reader-secret"})
        self.assertEqual(self.client.get("/api/v1/stocks/watchlist").json()["stock_codes"], ["aapl"])
        self.assertEqual(self.client.post("/api/v1/stocks/watchlist/remove", json={"stock_code": "AAPL"}).json()["stock_codes"], [])
        self.client.post("/api/v1/auth/logout")
        self.client.post("/api/v1/auth/login", json={"username": "owner", "password": "owner-secret"})
        self.assertEqual(self.client.get("/api/v1/stocks/watchlist").json()["stock_codes"], ["AAPL"])

    def test_watchlist_endpoints_reject_signed_out_requests(self):
        self.assertEqual(self.client.get("/api/v1/stocks/watchlist").status_code, 401)
        self.assertEqual(self.client.post("/api/v1/stocks/watchlist/add", json={"stock_code": "AAPL"}).status_code, 401)
        self.assertEqual(self.client.post("/api/v1/stocks/watchlist/remove", json={"stock_code": "AAPL"}).status_code, 401)

    def test_personal_notification_destinations_are_private_and_masked(self):
        path = "/api/v1/personal/notifications"
        self.assertEqual(self.client.get(path).status_code, 401)
        self.client.post("/api/v1/auth/register", json={
            "username": "owner", "password": "owner-secret", "passwordConfirm": "owner-secret",
        })
        self.assertEqual(self.client.get(path).status_code, 200)
        self.client.post("/api/v1/auth/logout")
        self.client.post("/api/v1/auth/register", json={
            "username": "reader1", "password": "reader-secret", "passwordConfirm": "reader-secret",
        })
        with patch.object(web_notification_channels.auth, "_get_data_dir", return_value=Path(self.temp.name)):
            saved = self.client.put(path, json={
                "channel": "email", "destination": "alice@example.com", "label": "我的邮箱", "enabled": True,
            })
            self.assertEqual(saved.status_code, 200)
            self.assertNotIn("alice@example.com", str(saved.json()))
            listed = self.client.get(path).json()["channels"]
            self.assertEqual(len(listed), 1)
            self.assertNotIn("alice@example.com", str(listed))
            self.assertNotIn("destination_encrypted", str(listed))
            channel_id = listed[0]["id"]
            self.client.post("/api/v1/auth/logout")
            self.client.post("/api/v1/auth/register", json={
                "username": "reader2", "password": "reader-secret", "passwordConfirm": "reader-secret",
            })
            self.assertEqual(self.client.get(path).json()["channels"], [])

    def test_scheduled_push_tasks_are_private_and_require_content(self):
        path = "/api/v1/personal/notifications/scheduled"
        self.client.post("/api/v1/auth/register", json={
            "username": "owner", "password": "owner-secret", "passwordConfirm": "owner-secret",
        })
        with patch.object(web_notification_channels.auth, "_get_data_dir", return_value=Path(self.temp.name)):
            saved = self.client.put(path, json={
                "name": "美股早报", "schedule_time": "08:00", "stock_codes": ["AAPL", "MSFT"],
                "channel": "email", "destination": "alice@example.com",
                "include_ai_analysis": True, "include_news_summary": True, "enabled": True,
            })
            self.assertEqual(saved.status_code, 200)
            task_id = saved.json()["id"]
            self.assertEqual(len(self.client.get(path).json()["tasks"]), 1)
            invalid = self.client.put(path, json={
                "name": "无内容", "schedule_time": "08:00", "stock_codes": ["AAPL"],
                "channel": "email", "destination": "alice@example.com",
                "include_ai_analysis": False, "include_news_summary": False, "enabled": True,
            })
            self.assertEqual(invalid.status_code, 400)
            self.client.post("/api/v1/auth/logout")
            self.client.post("/api/v1/auth/register", json={
                "username": "reader", "password": "reader-secret", "passwordConfirm": "reader-secret",
            })
            self.assertEqual(self.client.get(path).json()["tasks"], [])
            self.assertEqual(self.client.delete(f"{path}/{task_id}").status_code, 404)
            self.assertEqual(self.client.delete(f"{path}/{channel_id}").status_code, 404)
            self.assertEqual(self.client.put(path, json={
                "channel": "slack", "destination": "https://127.0.0.1/private", "label": "bad", "enabled": True,
            }).status_code, 400)
            self.client.post("/api/v1/auth/logout")
            self.client.post("/api/v1/auth/login", json={"username": "reader1", "password": "reader-secret"})
            self.assertEqual(len(self.client.get(path).json()["channels"]), 1)
            self.assertEqual(self.client.delete(f"{path}/{channel_id}").status_code, 200)
            self.assertEqual(self.client.get(path).json()["channels"], [])


if __name__ == "__main__":
    unittest.main()
