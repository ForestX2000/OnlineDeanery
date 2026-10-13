import unittest

from ml2.extract import extract_fields


class ConfiguredFieldsTests(unittest.TestCase):
    def test_custom_document_type_uses_configured_labels(self):
        definitions = [
            {"name": "invoice_number", "label": "Номер счёта", "aliases": ["Счёт №"],
             "reference": "custom-1", "kind": "text"},
            {"name": "received_date", "label": "Дата поступления", "aliases": [],
             "reference": "custom-1", "kind": "date"},
            {"name": "verified", "label": "Проверен", "aliases": [],
             "reference": "custom-1", "kind": "boolean", "must_be_true": True},
            {"name": "issue_date", "label": "Дата оплаты", "aliases": [],
             "reference": "custom-1", "kind": "date"},
        ]
        result = extract_fields(
            "Счёт №: А-42\nДата поступления: 12.09.2026\nПроверен: Да\n"
            "Дата документа: 01.01.2025 г. № 1\nДата оплаты: 15.03.2026",
            "custom_invoice",
            definitions,
        )

        self.assertEqual(result["invoice_number"], "А-42")
        self.assertEqual(result["received_date"], "12.09.2026")
        self.assertEqual(result["verified"], "Да")
        self.assertEqual(result["issue_date"], "15.03.2026")


if __name__ == "__main__":
    unittest.main()
