"""Проверки двух источников детектора (ml1/detector.py)."""

import os
import unittest

import numpy as np

from ml1.detector import detect_marks, letterbox, nms, unavailable

SIG_ONNX = os.getenv("TEST_SIG_ONNX", r"C:\Users\Nick\AppData\Local\Temp\opencode\kaggle_data\exp640\sig640.onnx")
STAMP_ONNX = os.getenv("TEST_STAMP_ONNX", r"C:\Users\Nick\AppData\Local\Temp\opencode\kaggle_data\runs\signature_stamp_v3\weights\best.onnx")
BATON = os.getenv("TEST_BATON_PNG", r"C:\Users\Nick\Downloads\baton.png")
WEIGHTS_AVAILABLE = os.path.exists(SIG_ONNX) and os.path.exists(STAMP_ONNX)


class MergeTests(unittest.TestCase):
    def setUp(self):
        self._saved = {k: os.environ.get(k) for k in (
            "YOLO_MODEL_PATH", "YOLO_SIG_MODEL_PATH", "YOLO_STAMP_HEURISTIC")}

    def tearDown(self):
        for key, value in self._saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_no_models_means_not_checked(self):
        os.environ.pop("YOLO_MODEL_PATH", None)
        os.environ.pop("YOLO_SIG_MODEL_PATH", None)
        os.environ["YOLO_STAMP_HEURISTIC"] = "0"
        result = detect_marks(np.zeros((64, 64, 3), dtype=np.uint8))
        self.assertEqual(result["status"], "disabled")
        self.assertIsNone(result["signature"])
        self.assertIsNone(result["stamp"])
        self.assertEqual(result["boxes"], [])

    def test_each_field_comes_from_own_source(self):
        # Один битый путь: его поле None, а не False.
        os.environ["YOLO_MODEL_PATH"] = r"C:\nonexistent\model.onnx"
        os.environ.pop("YOLO_SIG_MODEL_PATH", None)
        result = detect_marks(np.zeros((64, 64, 3), dtype=np.uint8))
        self.assertEqual(result["status"], "error")
        self.assertIsNone(result["stamp"])
        self.assertIsNone(result["signature"])

    def test_nms_keeps_strongest(self):
        boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [50, 50, 60, 60]], dtype=np.float32)
        self.assertEqual(nms(boxes, np.array([0.9, 0.5, 0.8])), [0, 2])

    def test_letterbox_is_square_and_reversible(self):
        img = np.zeros((100, 200, 3), dtype=np.uint8)
        tensor, scale, left, top = letterbox(img, 64)
        self.assertEqual(tensor.shape, (1, 3, 64, 64))
        self.assertAlmostEqual(scale, 64 / 200)

    @unittest.skipUnless(WEIGHTS_AVAILABLE, "нужны оба ONNX вне репозитория")
    def test_baton_finds_signature_and_stamp(self):
        import cv2
        os.environ["YOLO_SIG_MODEL_PATH"] = SIG_ONNX
        os.environ["YOLO_MODEL_PATH"] = STAMP_ONNX
        os.environ["YOLO_CONFIDENCE"] = "0.3"
        img = cv2.imread(BATON)
        result = detect_marks(img)
        self.assertEqual(result["status"], "ready")
        self.assertTrue(result["signature"], "Mels22 должен найти подпись на baton.png")
        self.assertTrue(result["stamp"], "своя модель должна найти печать на baton.png")


if __name__ == "__main__":
    unittest.main()
