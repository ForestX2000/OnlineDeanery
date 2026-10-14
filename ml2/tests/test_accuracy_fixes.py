"""Регресс-тесты точности извлечения (кейсы из прогона 12 документов).

Каждый тест привязан к реальному сбою:
- МЭИ (file-001): LaTeX-подчёркивания Paddle, «Подтверждает, что X действительно»;
- ВШЭ (file-002): «школа» в названии вуза, код после названия, № приказа;
- школа СОШ: не должна классифицироваться как study_certificate;
- «субботу», «дата рождения», «для предоставления по» — ложные срабатывания.
"""

import unittest

from ml2.classify import classify
from ml2.extract import extract_fields, extract_program, extract_student_name, extract_university
from ml2.ocr_fixes import apply_ocr_fixes


MEI_OCR = (
    "Подтверждает, что \\(\\underline{\\text{Гузенко Александр Сергеевич}}\\)\n"
    "действительно является студентом\n"
    "Приказ о зачислении № 5703/у от 04.08.2014 г. Окончание обучения 30.06.2019 г."
)

HSE_OCR = (
    "НАЦИОНАЛЬНЫЙ ИССЛЕДОВАТЕЛЬСКИЙ УНИВЕРСИТЕТ\n"
    "ВЫСШАЯ ШКОЛА ЭКОНОМИКИ\n"
    "Дана _______ Мульмановой Алене Сергеевне, 02.02.2001 г.р.\n"
    "направлению \"Востоковедение и африканистика\" (58.03.01).\n"
    "Зачислена на 1 курс с 01 сентября 2019 г. приказом от 20 августа 2019 г. №6.18.1-05/2008-08.\n"
    "Предполагаемый срок окончания обучения 30 июня 2024 г.\n"
    "Выдана для предоставления по месту требования"
)


class AccuracyFixesTests(unittest.TestCase):
    def test_latex_unwrap(self):
        fixed = apply_ocr_fixes(MEI_OCR)
        self.assertNotIn("underline", fixed)
        self.assertIn("Гузенко Александр Сергеевич", fixed)

    def test_mei_name_and_period(self):
        fields = extract_fields(apply_ocr_fixes(MEI_OCR), "study_certificate")
        self.assertEqual(fields["student_name"], "Гузенко Александр Сергеевич")
        self.assertEqual(fields["study_period"], "04.08.2014 – 30.06.2019")

    def test_hse_fields(self):
        fields = extract_fields(apply_ocr_fixes(HSE_OCR), "study_certificate")
        self.assertEqual(fields["student_name"], "Мульмановой Алене Сергеевне")
        self.assertIn("ВЫСШАЯ ШКОЛА ЭКОНОМИКИ", fields["university"])
        self.assertEqual(fields["program"], "58.03.01 Востоковедение и африканистика")
        self.assertEqual(fields["study_period"], "01.09.2019 – 30.06.2024")
        # № приказа — не номер справки.
        self.assertEqual(fields["document_number"], "не найдено")

    def test_school_not_study_certificate(self):
        doc_type, _ = classify("МБОУ СОШ 28 ученик 8Б класса школа. Обучается по очной форме.")
        self.assertEqual(doc_type, "неизвестно")

    def test_hse_with_school_word_is_study_certificate(self):
        doc_type, _ = classify(HSE_OCR)
        self.assertEqual(doc_type, "study_certificate")

    def test_no_false_university_from_weekday(self):
        self.assertIsNone(extract_university("в субботу с 08.30 до 13.40"))
        self.assertEqual(extract_university("Справка (ДГТУ). Зачислен с 01.09.2024."), "ДГТУ")

    def test_no_service_words_as_name(self):
        self.assertIsNone(extract_student_name("Выдана для предоставления по месту требования"))
        self.assertIsNone(extract_student_name("дата рождения 17.07.1965 в том, что"))
        self.assertEqual(
            extract_student_name("Подтверждает, что Гузенко Александр Сергеевич действительно является"),
            "Гузенко Александр Сергеевич",
        )

    def test_program_garbage_tail_cleaned(self):
        self.assertEqual(
            extract_program("программой 08.03.01 Строительство ы a"),
            "08.03.01 Строительство",
        )

    def test_school_number_not_document_number(self):
        fields = extract_fields("МБОУ СОШ № 28 города Северодвинска", "study_certificate")
        self.assertEqual(fields["document_number"], "не найдено")

    def test_holidays_not_study_period(self):
        fields = extract_fields(
            "Осенние каникулы с 29.10.2018 по 05.11.2018 года.", "study_certificate")
        self.assertEqual(fields["study_period"], "не найдено")


if __name__ == "__main__":
    unittest.main()
