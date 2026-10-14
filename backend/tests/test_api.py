import unittest
from io import BytesIO
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from PIL import Image
from pypdf import PdfWriter

from backend import api


class ApiTests(unittest.TestCase):
    def setUp(self):
        api.sessions.clear()
        api.active_sessions.clear()
        self.client = TestClient(api.app)
        self.client.__enter__()
        self.calls = []
        self.answer = {
            "answer": "Не хватает даты. См. п. 3.4 Положения.",
            "sources": [{"type": "положение", "reference": "п. 3.4"}],
            "verification": {"status": "incomplete", "missing_fields": ["issue_date"]},
        }

        async def upstream(url, **kwargs):
            self.calls.append((url, kwargs))
            if url == api.DOCUMENT_TYPES_URL:
                return {"items": [
                    {"id": "study_certificate", "required_fields": []},
                    {"id": "academic_leave", "required_fields": []},
                    {"id": "internship_certificate", "required_fields": []},
                ]}
            if url == api.ML1_URL:
                return {"text": "Иванов", "coordinates": [{"x": 1, "y": 2}]}
            if url == api.ML2_URL:
                return {"document_type": "study_certificate", "fields": {"name": "Иванов", "stamp": False}}
            return self.answer

        self.patcher = patch.object(api, "send_request", side_effect=upstream)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.client.__exit__(None, None, None)

    def image(self, format="PNG"):
        stream = BytesIO()
        Image.new("RGB", (10, 10)).save(stream, format=format)
        return stream.getvalue()

    def analyze(self, name="scan.png", content=None, **data):
        return self.client.post("/analyze", data={"question": "Подходит?", **data},
                                files={"file": (name, self.image() if content is None else content)})

    def test_chat_and_follow_up_history(self):
        response = self.client.post("/chat", json={"message": "  Вопрос?  "})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIsNone(data["document"])
        self.assertEqual(self.calls[0][0], api.BACKEND2_URL)
        self.assertEqual(self.calls[0][1]["json"]["question"], "Вопрос?")
        self.assertEqual(self.calls[0][1]["json"]["history"], [])
        follow_up = self.client.post("/chat", json={"message": "Почему?", "conversation_id": data["conversation_id"]})
        self.assertEqual(follow_up.status_code, 200)
        self.assertEqual(len(self.calls[-1][1]["json"]["history"]), 2)

    def test_analyze_routes_all_services_and_preserves_document(self):
        response = self.analyze(document_type="academic_leave")
        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()
        self.assertEqual([url for url, _ in self.calls],
                         [api.DOCUMENT_TYPES_URL, api.ML1_URL, api.ML2_URL, api.BACKEND2_URL])
        self.assertEqual(self.calls[1][1]["files"]["file"][2], "image/png")
        self.assertEqual(self.calls[2][1]["json"]["document_type"], "academic_leave")
        self.assertEqual(data["document"]["fields"]["stamp"], False)
        self.assertEqual(data["document"]["coordinates"], [{"x": 1, "y": 2}])
        self.assertEqual(data["verification"]["missing_fields"], ["issue_date"])
        self.assertEqual(data["verification"]["issues"], [])
        follow_up = self.client.post("/chat", json={"message": "Чего не хватает?", "conversation_id": data["conversation_id"]})
        self.assertEqual(follow_up.json()["document"], data["document"])
        self.assertEqual(self.calls[-1][1]["json"]["document"], data["document"])

    def test_valid_jpeg_and_pdf(self):
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        stream = BytesIO()
        writer.write(stream)
        for name, content in [("scan.JPG", self.image("JPEG")), ("scan.pdf", stream.getvalue())]:
            with self.subTest(name=name):
                self.assertEqual(self.analyze(name, content).status_code, 200)

    def test_bad_uploads_never_reach_ml(self):
        for name, content, status in [
            ("scan.exe", b"x", 400), ("scan.png", b"", 400),
            ("scan.jpg", self.image(), 400), ("scan.png", b"bad", 400),
            ("scan.pdf", b"bad", 400), ("scan.pdf", b"%PDF-bad", 400),
            ("scan.png", b"x" * (api.MAX_FILE_SIZE + 1), 413),
        ]:
            with self.subTest(name=name, status=status):
                self.assertEqual(self.analyze(name, content).status_code, status)
        self.assertEqual(self.calls, [])

    def test_encrypted_pdf_is_rejected(self):
        writer = PdfWriter()
        writer.add_blank_page(width=100, height=100)
        writer.encrypt("password")
        stream = BytesIO()
        writer.write(stream)
        self.assertEqual(self.analyze("scan.pdf", stream.getvalue()).status_code, 400)

    def test_question_is_required_for_both_routes(self):
        self.assertEqual(self.client.post("/chat", json={"message": "  "}).status_code, 400)
        self.assertEqual(self.analyze(question="  ").status_code, 400)
        self.assertEqual(self.client.post("/chat", json={}).status_code, 422)
        self.assertEqual(self.client.post("/chat", json={"message": "x" * 5001}).status_code, 422)
        self.assertEqual(self.analyze(document_type="unknown").status_code, 422)
        self.assertTrue(all(url == api.DOCUMENT_TYPES_URL for url, _ in self.calls),
                        "неизвестный тип отклоняется до обращения к ML/Backend2")

    def test_unknown_expired_and_busy_sessions(self):
        self.assertEqual(self.client.post("/chat", json={"message": "?", "conversation_id": "missing"}).status_code, 404)
        import time as _time
        api.sessions["expired"] = api.Session(updated_at=_time.monotonic() - api.SESSION_TTL_SECONDS - 1)
        self.assertEqual(self.client.post("/chat", json={"message": "?", "conversation_id": "expired"}).status_code, 404)
        api.sessions["busy"] = api.Session()
        api.active_sessions.add("busy")
        self.assertEqual(self.client.post("/chat", json={"message": "?", "conversation_id": "busy"}).status_code, 409)

    def test_invalid_service_answer_does_not_change_session(self):
        first = self.analyze().json()
        session = api.sessions[first["conversation_id"]]
        history = list(session.history)
        for invalid in [{"answer": "ok", "sources": None}, {"answer": " "}, {"answer": 123}]:
            self.answer = invalid
            response = self.client.post("/chat", json={"message": "?", "conversation_id": first["conversation_id"]})
            self.assertEqual(response.status_code, 502)
            self.assertEqual(session.history, history)
            self.assertNotIn(first["conversation_id"], api.active_sessions)

    def test_invalid_ml_output_does_not_create_a_session(self):
        for payload in [{"text": 42}, {"text": "ok", "coordinates": "bad"}]:
            with patch.object(api, "send_request", return_value=payload):
                self.assertEqual(self.analyze().status_code, 502)
        with patch.object(api, "send_request", side_effect=[{"text": "ok"}, {"fields": []}]):
            self.assertEqual(self.analyze().status_code, 502)
        self.assertEqual(api.sessions, {})
        self.assertEqual(api.active_sessions, set())

    def test_cors_preflight(self):
        response = self.client.options("/analyze", headers={
            "Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def test_transport_errors(self):
        cases = [
            (httpx.ReadTimeout("slow"), 504), (httpx.ConnectError("offline"), 503),
            (httpx.Response(500), 502), (httpx.Response(200, text="not json"), 502),
            (httpx.Response(200, json=[]), 502),
        ]
        for outcome, status in cases:
            with self.subTest(status=status, outcome=outcome):
                def handler(request):
                    if isinstance(outcome, Exception):
                        raise outcome
                    return outcome

                async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                    api.app.state.http_client = client
                    with self.assertRaises(api.HTTPException) as caught:
                        await api.send_request("http://service/answer", json={})
                    self.assertEqual(caught.exception.status_code, status)


if __name__ == "__main__":
    unittest.main()
