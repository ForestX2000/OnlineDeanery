"""Регресс-тесты security-фиксов (plaintext-пароли, открытая админка, TTL)."""

import unittest

from fastapi.testclient import TestClient

from backend import api
from backend.security import hash_password, verify_password


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(api.app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)

    def test_hash_roundtrip(self):
        stored = hash_password("correct horse")
        self.assertTrue(stored.startswith("pbkdf2$"))
        self.assertNotIn("correct horse", stored)
        self.assertEqual(verify_password("correct horse", stored), "ok")
        self.assertEqual(verify_password("wrong", stored), "invalid")

    def test_legacy_plaintext_detected_once(self):
        self.assertEqual(verify_password("123456", "123456"), "legacy")
        self.assertEqual(verify_password("other", "123456"), "invalid")
        self.assertEqual(verify_password("пароль", "пароль"), "legacy")

    def test_tampered_hash_rejected(self):
        stored = hash_password("secret")
        self.assertEqual(verify_password("secret", stored + "x"), "invalid")
        self.assertEqual(verify_password("secret", "garbage"), "invalid")

    def test_admin_create_requires_auth(self):
        response = self.client.post("/api/admin/users", json={
            "email": "evil@x.ru", "password": "longenoughpassword", "username": "Evil", "role": "admin",
        })
        # Без токена — 401, а не создание пользователя.
        self.assertEqual(response.status_code, 401)

    def test_weak_password_and_role_rejected(self):
        # Валидация тела — на уровне pydantic-модели (endpoint требует
        # auth раньше body, см. test_admin_create_requires_auth).
        from pydantic import ValidationError
        from backend.api import CreateUserRequest
        with self.assertRaises(ValidationError):
            CreateUserRequest(email="evil@x.ru", password="123",
                              username="Evil", role="superadmin")
        with self.assertRaises(ValidationError):
            CreateUserRequest(email="evil@x.ru", password="x" * 11,
                              username="Evil", role="student")
        with self.assertRaises(ValidationError):
            CreateUserRequest(email="not-an-email", password="longenoughpassword",
                              username="Evil", role="student")

    def test_login_validation(self):
        response = self.client.post("/api/auth/login", json={
            "email": "not-an-email", "password": "x",
        })
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
