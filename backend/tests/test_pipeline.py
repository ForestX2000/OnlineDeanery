"""Реальные API 1 и Backend 2; только ML заменены предсказуемыми ответами."""

import json
import unittest
from io import BytesIO

import httpx
from fastapi.testclient import TestClient
from PIL import Image

from backend import api, logic


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.logic_client = TestClient(logic.app)
        self.logic_client.__enter__()
        self.api_client = TestClient(api.app)
        self.api_client.__enter__()
        self.fields = {}
        self.calls = []
        self.transport = httpx.MockTransport(self.dispatch)
        self.client = httpx.AsyncClient(transport=self.transport)
        self.original_client = api.app.state.http_client
        api.app.state.http_client = self.client

    def tearDown(self):
        self.api_client.portal.call(self.client.aclose)
        api.app.state.http_client = self.original_client
        self.api_client.__exit__(None, None, None)
        self.logic_client.__exit__(None, None, None)

    async def dispatch(self, request):
        url = str(request.url)
        self.calls.append(url)
        if url == api.ML1_URL:
            return httpx.Response(200, json={"text": "Тестовый документ", "coordinates": []})
        if url == api.ML2_URL:
            return httpx.Response(200, json={"document_type": "study_certificate", "fields": self.fields})
        self.assertEqual(url, api.BACKEND2_URL)
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=logic.app), base_url="http://logic") as client:
            return await client.post("/answer", json=json.loads(request.content))

    def upload(self):
        stream = BytesIO()
        Image.new("RGB", (10, 10)).save(stream, format="PNG")
        return self.api_client.post("/analyze", data={"question": "Хватит ли этой справки?"},
                                    files={"file": ("scan.png", stream.getvalue(), "image/png")})

    def test_complete_incomplete_and_unknown_answer_with_real_logic(self):
        base = logic.app.state.knowledge_base
        self.fields = {rule.name: (True if rule.kind == "boolean" else "10.10.2026" if rule.kind == "date" else "Тестовое значение")
                       for rule in base.document_types["study_certificate"].required_fields}
        complete = self.upload()
        self.assertEqual(complete.status_code, 200, complete.text)
        self.assertEqual(complete.json()["verification"]["status"], "complete")
        self.assertEqual(self.calls, [api.ML1_URL, api.ML2_URL, api.BACKEND2_URL])
        self.assertTrue(all(source["type"] == "описание кейса" for source in complete.json()["sources"]))

        del self.fields["issue_date"]
        self.fields["stamp"] = False
        incomplete = self.upload().json()
        self.assertEqual(incomplete["verification"]["status"], "incomplete")
        self.assertIn("issue_date", incomplete["verification"]["missing_fields"])
        self.assertTrue(incomplete["verification"]["issues"])

        response = self.api_client.post("/chat", json={
            "message": "Сколько стоит обучение?", "conversation_id": incomplete["conversation_id"],
        })
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIn("Ответа нет", response.json()["answer"])
        self.assertEqual(response.json()["document"], incomplete["document"])
        self.assertEqual(self.calls[-1], api.BACKEND2_URL)

    def test_question_without_document_reaches_rule_search(self):
        response = self.api_client.post("/chat", json={"message": "Какие поля нужны в справке об обучении?"})
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()["document"])
        self.assertIsNone(response.json()["verification"])
        self.assertIn("ФИО", response.json()["answer"])
        self.assertTrue(response.json()["sources"])
        self.assertEqual(self.calls, [api.BACKEND2_URL])
