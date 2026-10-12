"""The optional model selects evidence; it cannot author claims or verdicts."""

import asyncio
import json
import os
import time
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient

from backend import logic
from backend.answer_llm import AnswerLlmSettings, build_catalog, parse_selection, select_evidence
from backend.models import Document
from backend.rules import KnowledgeBase, NO_ANSWER_TEXT, answer_question


def example_base():
    return KnowledgeBase.model_validate({
        "title": "Учебный пример, не реальный регламент",
        "scope_note": "Тестовые требования не являются правилами вуза.",
        "clauses": [
            {"id": "1.1", "text": "Заявление на академический отпуск подается до 15 октября.",
             "topics": ["срок подачи", "академический отпуск"],
             "document_types": ["academic_leave"], "url": "https://example.edu/rules#1.1"},
            {"id": "1.2", "text": "В заявлении обязательны ФИО и подпись студента.",
             "topics": ["обязательные поля"], "document_types": ["academic_leave"]},
        ],
        "document_types": {
            "academic_leave": {
                "label": "Заявление на академический отпуск",
                "required_fields": [
                    {"name": "full_name", "label": "ФИО", "aliases": ["name"], "reference": "1.2"},
                    {"name": "signature", "label": "Подпись студента", "kind": "boolean",
                     "must_be_true": True, "reference": "1.2"},
                ],
            },
        },
    })


def completion(selection=None, **choice_fields):
    if selection is None:
        selection = {"supported": True, "clause_ids": ["1.1"], "field_ids": []}
    choice = {"finish_reason": "stop", "message": {"content": json.dumps(selection, ensure_ascii=False)}}
    choice.update(choice_fields)
    return {"choices": [choice]}


class SelectionValidationTests(unittest.TestCase):
    def test_rejects_invented_ids_prose_and_verdicts(self):
        selections = [
            {"supported": True, "clause_ids": ["9.9"], "field_ids": []},
            {"supported": True, "clause_ids": [], "field_ids": ["tuition"]},
            {"supported": True, "clause_ids": ["1.1", "1.1"], "field_ids": []},
            {"supported": True, "clause_ids": ["1.1"], "field_ids": [], "answer": "Срок 20 октября"},
            {"supported": True, "clause_ids": ["1.1"], "field_ids": [], "verification": "complete"},
            {"supported": "true", "clause_ids": ["1.1"], "field_ids": []},
            {"supported": False, "clause_ids": ["1.1"], "field_ids": []},
            {"supported": True, "clause_ids": [], "field_ids": []},
        ]
        for selected in selections:
            with self.subTest(selected=selected):
                self.assertIsNone(parse_selection(completion(selected), {"1.1"}, {"full_name"}))

    def test_rejects_truncation_missing_status_refusal_and_bad_envelope(self):
        for payload in (
            None, [], {}, {"choices": []},
            completion(finish_reason="length"), completion(finish_reason=None),
            completion(message={"content": "not JSON"}),
            completion(message={"content": "{}", "refusal": "refused"}),
            completion(message={"content": "{}", "tool_calls": [{"name": "invent"}]}),
        ):
            with self.subTest(payload=payload):
                self.assertIsNone(parse_selection(payload, {"1.1"}, set()))

    def test_accepts_existing_ids_only(self):
        result = parse_selection(completion(), {"1.1"}, set())
        self.assertEqual(result.clause_ids, ["1.1"])

    def test_catalog_has_no_ocr_text_values_or_assistant_claims(self):
        document = Document(type="academic_leave", fields={"full_name": "PERSONAL VALUE"}, ocr_text="UNTRUSTED OCR")
        content = json.dumps(build_catalog(example_base(), document), ensure_ascii=False)
        self.assertIn("full_name", content)
        self.assertNotIn("PERSONAL VALUE", content)
        self.assertNotIn("UNTRUSTED OCR", content)


class SettingsTests(unittest.TestCase):
    def test_disabled_without_configured_endpoint(self):
        with patch.dict(os.environ, {"ANSWER_LLM_URL": ""}):
            self.assertIsNone(AnswerLlmSettings.from_env())

    def test_time_and_token_limits_are_capped(self):
        settings = AnswerLlmSettings("http://llama:8080/v1/chat/completions", timeout=120, max_tokens=4096)
        self.assertEqual(settings.timeout, 15)
        self.assertEqual(settings.max_tokens, 512)

    def test_invalid_configuration_disables_optional_feature(self):
        for setting in ({"ANSWER_LLM_TIMEOUT": "nan"}, {"ANSWER_LLM_TIMEOUT": "-1"},
                        {"ANSWER_LLM_MAX_TOKENS": "bad"}, {"ANSWER_LLM_URL": "file:///tmp/model"}):
            values = {"ANSWER_LLM_URL": "http://localhost:8081/v1/chat/completions",
                      "ANSWER_LLM_TIMEOUT": "8", "ANSWER_LLM_MAX_TOKENS": "256", **setting}
            with self.subTest(setting=setting), patch.dict(os.environ, values), self.assertLogs("backend.answer_llm", level="WARNING"):
                self.assertIsNone(AnswerLlmSettings.from_env())


class SelectorTests(unittest.IsolatedAsyncioTestCase):
    async def test_no_network_when_disabled_empty_or_prompt_too_large(self):
        calls = []
        async def handler(request):
            calls.append(request)
            return httpx.Response(200, json=completion())
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            settings = AnswerLlmSettings("http://llama/v1/chat/completions")
            for base, configured in ((example_base(), None), (KnowledgeBase(), settings)):
                self.assertIsNone(await select_evidence(base, "вопрос", None, [], configured, client))
            huge = example_base()
            huge.clauses[0].text = "x" * 25000
            self.assertIsNone(await select_evidence(huge, "вопрос", None, [], settings, client))
        self.assertEqual(calls, [])

    async def test_total_deadline_cancels_slow_server(self):
        cancelled = []
        async def slow(request):
            try:
                await asyncio.sleep(10)
            finally:
                cancelled.append(True)
            return httpx.Response(200, json=completion())
        async with httpx.AsyncClient(transport=httpx.MockTransport(slow)) as client:
            started = time.monotonic()
            result = await select_evidence(example_base(), "вопрос", None, [],
                                           AnswerLlmSettings("http://llama/v1/chat/completions", timeout=0.02), client)
            self.assertIsNone(result)
            self.assertLess(time.monotonic() - started, 1)
        self.assertTrue(cancelled)

    async def test_http_failure_timeout_bad_json_and_redirect_fall_back(self):
        for outcome in (httpx.Response(503), httpx.Response(302, headers={"location": "https://example.com"}),
                        httpx.Response(200, text="invalid JSON"), httpx.ReadTimeout("slow")):
            async def handler(request):
                if isinstance(outcome, Exception):
                    raise outcome
                return outcome
            with self.subTest(outcome=outcome):
                async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                    self.assertIsNone(await select_evidence(example_base(), "вопрос", None, [],
                        AnswerLlmSettings("http://llama/v1/chat/completions"), client))


class AnswerIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"ANSWER_LLM_URL": ""})
        self.environment.start()
        self.client = TestClient(logic.app)
        self.client.__enter__()
        self.base = example_base()
        logic.app.state.knowledge_base = self.base
        self.llm_client = None
        self.requests = []

    def tearDown(self):
        if self.llm_client is not None:
            self.client.portal.call(self.llm_client.aclose)
        self.client.__exit__(None, None, None)
        self.environment.stop()

    def configure(self, response):
        def handler(request):
            self.requests.append(json.loads(request.content))
            return httpx.Response(200, json=response)
        self.llm_client = httpx.AsyncClient(transport=httpx.MockTransport(handler))
        logic.app.state.answer_llm_settings = AnswerLlmSettings("http://llama/v1/chat/completions", model="local-qwen")
        logic.app.state.answer_llm_client = self.llm_client

    def answer(self, question, document=None):
        payload = {"question": question}
        if document is not None:
            payload["document"] = document.model_dump()
        result = self.client.post("/answer", json=payload)
        self.assertEqual(result.status_code, 200, result.text)
        return result.json()

    def test_semantic_paraphrase_returns_exact_clause_and_real_source(self):
        question = "До какого числа мне надо принести бумаги, чтобы сделать перерыв в учебе?"
        self.assertTrue(answer_question(self.base, question, None, [])["answer"].startswith(NO_ANSWER_TEXT))
        self.configure(completion())
        result = self.answer(question)
        self.assertIn(self.base.clauses[0].text, result["answer"])
        self.assertIn(self.base.scope_note, result["answer"])
        self.assertNotIn(NO_ANSWER_TEXT, result["answer"])
        self.assertEqual(result["sources"][0]["url"], "https://example.edu/rules#1.1")
        self.assertIsNone(result["verification"])
        self.assertEqual(self.requests[0]["model"], "local-qwen")
        self.assertLessEqual(self.requests[0]["max_tokens"], 512)
        self.assertEqual(self.requests[0]["temperature"], 0)

    def test_field_paraphrase_uses_actual_value_and_preserves_failed_check(self):
        self.configure(completion({"supported": True, "clause_ids": [], "field_ids": ["full_name"]}))
        document = Document(type="academic_leave", fields={"full_name": "Иванов Иван", "signature": False})
        question = "Как зовут автора этой бумаги?"
        expected = answer_question(self.base, question, document, [])
        result = self.answer(question, document)
        self.assertIn("ФИО — Иванов Иван", result["answer"])
        self.assertEqual(result["verification"], expected["verification"])
        self.assertEqual(result["verification"]["status"], "incomplete")
        self.assertIn("отсутствует", result["answer"])
        self.assertIn("Окончательное решение", result["answer"])
        self.assertTrue(any(source["type"] == "документ" for source in result["sources"]))

    def test_known_questions_do_not_wait_for_llm(self):
        self.configure(completion())
        question = "Срок подачи заявления на академический отпуск?"
        result = self.answer(question)
        self.assertEqual(result, answer_question(self.base, question, None, []))
        self.assertEqual(self.requests, [])

    def test_disabled_endpoint_keeps_original_deterministic_answer(self):
        question = "Сколько стоит заявление?"
        self.assertEqual(self.answer(question), answer_question(self.base, question, None, []))
        self.assertIsNone(logic.app.state.answer_llm_client)

    def test_fabricated_sources_or_no_support_leave_exact_fallback(self):
        for selected in (
            {"supported": True, "clause_ids": ["9.9"], "field_ids": []},
            {"supported": False, "clause_ids": [], "field_ids": []},
        ):
            with self.subTest(selected=selected):
                if self.llm_client is not None:
                    self.client.portal.call(self.llm_client.aclose)
                self.configure(completion(selected))
                question = "Сколько стоит заявление?"
                self.assertEqual(self.answer(question), answer_question(self.base, question, None, []))


if __name__ == "__main__":
    unittest.main()
