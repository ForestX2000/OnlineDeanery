import unittest
from copy import deepcopy

from pydantic import ValidationError

from backend.logic import DEFAULT_RULES_PATH
from backend.models import Document
from backend.rules import KnowledgeBase, answer_question, check_document, load_knowledge_base


class RulesTests(unittest.TestCase):
    def setUp(self):
        self.base = load_knowledge_base(DEFAULT_RULES_PATH)

    def complete(self, kind="academic_leave"):
        fields = {field.name: (True if field.kind == "boolean" else "10.10.2026" if field.kind == "date" else "Тестовое значение")
                  for field in self.base.document_types[kind].required_fields}
        return Document(type=kind, fields=fields)

    def test_content_question_lists_document_fields(self):
        for question in ["Что написано в документе?", "Что там написано?", "О чём говорится в справке?", "Перескажи документ"]:
            with self.subTest(question=question):
                result = answer_question(self.base, question, self.complete("study_certificate"), [])
                self.assertNotIn("Ответа нет", result["answer"])
                self.assertIn("Содержание документа", result["answer"])
                self.assertTrue(any(item["type"] == "документ" for item in result["sources"]))

    def test_other_intents_are_not_answered_by_field_presence(self):
        document = self.complete()
        for question in ["Какая стоимость курса?", "Кто должен ставить подпись?",
                         "Можно ли продлить академический отпуск?",
                         "В каком порядке выдаются справки?",
                         "Как проверить подлинность справки?",
                         "Достаточно ли 100 баллов для поступления?"]:
            with self.subTest(question=question):
                result = answer_question(self.base, question, document, [])
                self.assertTrue(result["answer"].startswith("Ответа нет"), result["answer"])
                self.assertFalse(any(item["type"] == "документ" for item in result["sources"]))

    def test_partial_lexical_match_cannot_answer_cost_question(self):
        for question in ["Стоимость справки об обучении?", "Сколько стоит обучение?", "Цена заявления на академический отпуск?"]:
            with self.subTest(question=question):
                result = answer_question(self.base, question, None, [])
                self.assertIn("Ответа нет", result["answer"])
                self.assertEqual(result["sources"], [])

    def test_explicit_field_question_returns_value_with_document_source(self):
        result = answer_question(self.base, "Какой номер документа?", self.complete("study_certificate"), [])
        self.assertIn("По данным документа: Номер документа", result["answer"])
        self.assertTrue(any(item["type"] == "документ" for item in result["sources"]))

    def test_question_can_change_type_while_retaining_document_check(self):
        result = answer_question(self.base, "Какие поля заявления на академический отпуск?", self.complete("study_certificate"), [])
        self.assertNotIn("Ответа нет", result["answer"])
        self.assertIn("причина отпуска", result["answer"])
        self.assertEqual(result["verification"]["status"], "complete")

    def test_missing_text_sentinels_do_not_pass(self):
        for value in ["не найдено", "нет", "отсутствует", "-", {"value": None}]:
            with self.subTest(value=value):
                document = self.complete()
                document.fields["student_name"] = value
                result, _, _ = check_document(self.base, document.type, document.fields)
                self.assertEqual(result["status"], "incomplete")
                self.assertIn("student_name", result["missing_fields"])

    def test_boolean_false_is_a_known_absence_not_missing_ocr(self):
        document = self.complete()
        document.fields["signature"] = "нет"
        result, _, _ = check_document(self.base, document.type, document.fields)
        self.assertEqual(result["status"], "incomplete")
        self.assertNotIn("signature", result["missing_fields"])
        self.assertIn("отсутствует", result["issues"][0])

    def test_conflicting_aliases_prevent_complete_result(self):
        document = self.complete()
        document.fields["name"] = "Другой человек"
        result, _, _ = check_document(self.base, document.type, document.fields)
        self.assertEqual(result["status"], "incomplete")
        self.assertTrue(any("противоречивые" in issue for issue in result["issues"]))

    def test_empty_type_alias_and_dangling_reference_rejected(self):
        original = self.base.model_dump()
        for mode in ["empty_type", "empty_field", "empty_alias", "dangling_reference"]:
            data = deepcopy(original)
            document = data["document_types"]["academic_leave"]
            if mode == "empty_type":
                data["document_types"][" "] = data["document_types"].pop("academic_leave")
            elif mode == "empty_field":
                document["required_fields"][0]["name"] = "__"
            elif mode == "empty_alias":
                document["aliases"].append(" ")
            else:
                document["required_fields"][0]["reference"] = "unknown"
            with self.subTest(mode=mode), self.assertRaises(ValidationError):
                KnowledgeBase.model_validate(data)

    def test_date_order_can_be_configured(self):
        data = self.base.model_dump()
        data["document_types"]["academic_leave"]["date_orders"] = [{
            "start": "start_date", "end": "end_date", "reference": "3.2",
        }]
        base = KnowledgeBase.model_validate(data)
        document = self.complete()
        document.fields.update(start_date="2026-10-20", end_date="2026-10-10")
        result, _, _ = check_document(base, document.type, document.fields)
        self.assertEqual(result["status"], "incomplete")
        self.assertTrue(any("позже" in issue for issue in result["issues"]))
