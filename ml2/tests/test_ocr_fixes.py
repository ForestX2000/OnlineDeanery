"""Проверки словаря OCR-исправлений (message.txt, вариант A)."""

import unittest

from ml2.ocr_fixes import OCR_FIXES, apply_ocr_fixes


class OcrFixesTests(unittest.TestCase):
    def test_message_txt_examples(self):
        bad = (
            "Батальников Данил Серевич (10.06.2006 г. р.) дебютгельно кладется обучающиеся "
            "Лонкего государственного технического университета. "
            "09.02.07 Ниформалонные системы и программрование. "
            "«ДОМСКОН ГОСУДАРСТВЕННЫЙ ТЭХНИГСКИЙ УНИВЕСКАТЬ» (ЛТУ)"
        )
        fixed = apply_ocr_fixes(bad)
        for expected in (
            "Даниил", "Сергеевич", "действительно", "является",
            "Донского", "Информационные", "программирование",
            "ДОНСКОЙ", "ТЕХНИЧЕСКИЙ", "УНИВЕРСИТЕТ", "ДГТУ",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, fixed)

    def test_measured_baton_errors(self):
        bad = "МИНИСТЕРСТВО НАУКИ И ВЫСПИЕГО ОБРАЗОВАНИЯ «ГОНСКОЙ ГОСУДАРСТВЕННЫЙ ТЕХНИЧЕСКИЙ (ДТУ)"
        fixed = apply_ocr_fixes(bad)
        self.assertIn("ВЫСШЕГО", fixed)
        self.assertIn("ГОНСКОЙ".replace("ГОНСКОЙ", "ДОНСКОЙ"), fixed)
        self.assertIn("ДГТУ", fixed)
        self.assertNotIn("ВЫСПИЕГО", fixed)

    def test_case_restoration(self):
        self.assertEqual(apply_ocr_fixes("данил"), "даниил")
        self.assertEqual(apply_ocr_fixes("Данил"), "Даниил")
        self.assertEqual(apply_ocr_fixes("ДАНИЛ"), "ДАНИИЛ")

    def test_whole_word_only(self):
        # Части слов не трогаем: «Данилович» — фамилия, а не ошибка в «Данил».
        self.assertEqual(apply_ocr_fixes("Данилович"), "Данилович")
        self.assertEqual(apply_ocr_fixes("колледжный"), "колледжный")

    def test_clean_text_untouched(self):
        good = "Батальчиков Даниил Сергеевич, Донской государственный технический университет (ДГТУ)."
        self.assertEqual(apply_ocr_fixes(good), good)

    def test_empty_and_non_string(self):
        self.assertEqual(apply_ocr_fixes(""), "")
        self.assertIsNone(apply_ocr_fixes(None))

    def test_dict_not_empty(self):
        self.assertGreater(len(OCR_FIXES), 10)


if __name__ == "__main__":
    unittest.main()
