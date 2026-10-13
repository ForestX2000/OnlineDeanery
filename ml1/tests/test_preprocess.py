import unittest
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageDraw

from ml1.preprocess import estimate_rotation, estimate_skew, prepare_image, preprocess


def encode(image: Image.Image, **kwargs) -> bytes:
    stream = BytesIO()
    image.save(stream, format="PNG", **kwargs)
    return stream.getvalue()


def rgb(pixels: np.ndarray) -> np.ndarray:
    return pixels[:, :, ::-1]


class PreprocessTests(unittest.TestCase):
    def test_white_page_preserves_black_and_faint_text(self):
        page = Image.new("RGB", (400, 600), "white")
        draw = ImageDraw.Draw(page)
        for index, shade in enumerate((0, 120, 220, 245, 250)):
            draw.text((20, 20 + index * 30), "Student 2026 / 07-6540", fill=(shade,) * 3)
        original = np.array(page)
        self.assertTrue(np.any(np.all(original == 250, axis=2)))

        result = preprocess(encode(page))

        np.testing.assert_array_equal(rgb(result), original)
        self.assertEqual(result.shape, (600, 400, 3))

    def test_tall_upright_document_is_not_rotated_or_resized(self):
        page = Image.new("RGB", (100, 400), "white")
        draw = ImageDraw.Draw(page)
        draw.text((10, 10), "TOP", fill="black")
        draw.text((10, 370), "BOTTOM", fill="black")

        result = preprocess(encode(page))

        self.assertEqual(result.shape, (400, 100, 3))
        np.testing.assert_array_equal(rgb(result), np.array(page))

    def test_transparent_page_is_composited_on_white(self):
        page = Image.new("RGBA", (3, 1))
        page.putdata([(0, 0, 0, 0), (0, 0, 0, 255), (0, 0, 0, 128)])

        result = preprocess(encode(page))

        np.testing.assert_array_equal(
            rgb(result), [[[255, 255, 255], [0, 0, 0], [127, 127, 127]]]
        )

    def test_palette_transparency_is_composited_on_white(self):
        page = Image.new("P", (2, 1))
        page.putpalette([0, 0, 0, 10, 20, 30] + [0] * 762)
        page.putdata([0, 1])

        result = preprocess(encode(page, transparency=0))

        np.testing.assert_array_equal(rgb(result), [[[255, 255, 255], [10, 20, 30]]])

    def test_grayscale_strokes_remain_grayscale(self):
        page = Image.fromarray(np.array([[0, 200, 250, 255]], dtype=np.uint8))

        result = preprocess(encode(page))

        np.testing.assert_array_equal(
            result, [[[0, 0, 0], [200, 200, 200], [250, 250, 250], [255, 255, 255]]]
        )

    def test_colors_survive_the_ocr_png_encoder(self):
        page = Image.new("RGB", (3, 1))
        page.putdata([(255, 0, 0), (0, 255, 0), (0, 0, 255)])

        result = preprocess(encode(page))
        success, encoded = cv2.imencode(".png", result)

        self.assertTrue(success)
        self.assertEqual(result.dtype, np.uint8)
        self.assertTrue(result.flags.c_contiguous)
        with Image.open(BytesIO(encoded.tobytes())) as decoded:
            np.testing.assert_array_equal(np.array(decoded), np.array(page))

    def test_exif_orientation_is_applied(self):
        page = Image.fromarray(np.arange(18, dtype=np.uint8).reshape(2, 3, 3))
        exif = Image.Exif()
        exif[274] = 6  # Camera metadata: display 90 degrees clockwise.

        result = preprocess(encode(page, exif=exif))

        np.testing.assert_array_equal(rgb(result), np.rot90(np.array(page), k=-1))

    def test_explicit_clockwise_rotation_preserves_all_pixels(self):
        page = Image.fromarray(np.arange(18, dtype=np.uint8).reshape(2, 3, 3))
        data = encode(page)
        for rotation in (0, 90, 180, 270):
            with self.subTest(rotation=rotation):
                result = preprocess(data, rotation=rotation)
                np.testing.assert_array_equal(
                    rgb(result), np.rot90(np.array(page), k=-(rotation // 90))
                )

    def test_explicit_rotation_is_applied_after_exif(self):
        page = Image.fromarray(np.arange(18, dtype=np.uint8).reshape(2, 3, 3))
        exif = Image.Exif()
        exif[274] = 2  # Horizontal mirror; unlike a rotation, order matters here.

        result = preprocess(encode(page, exif=exif), rotation=90)

        np.testing.assert_array_equal(
            rgb(result), np.rot90(np.array(page)[:, ::-1], k=-1)
        )

    def test_invalid_rotation_is_rejected(self):
        data = encode(Image.new("RGB", (2, 2)))
        for rotation in (-90, 45, 360, "90", None, True):
            with self.subTest(rotation=rotation), self.assertRaisesRegex(ValueError, "Поворот"):
                preprocess(data, rotation=rotation)

    def test_invalid_and_truncated_images_are_rejected(self):
        valid_png = encode(Image.new("RGB", (2, 2)))
        for data in (b"", b"not an image", valid_png[:40]):
            with self.subTest(data=data), self.assertRaisesRegex(ValueError, "декодировать"):
                preprocess(data)


def text_page(width=600, height=400, lines=10) -> Image.Image:
    page = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(page)
    for i in range(lines):
        draw.text((30, 20 + i * 35), f"Донской государственный технический университет {i}", fill="black")
    return page


def gray_of(image: Image.Image) -> np.ndarray:
    return np.asarray(image.convert("L"))


class OrientationTests(unittest.TestCase):
    def test_upright_page_is_zero(self):
        self.assertEqual(estimate_rotation(gray_of(text_page())), 0)

    def test_sideways_page_is_90(self):
        sideways = text_page().transpose(Image.Transpose.ROTATE_90)
        self.assertEqual(estimate_rotation(gray_of(sideways)), 90)

    def test_blank_page_is_zero(self):
        self.assertEqual(estimate_rotation(np.full((400, 600), 255, dtype=np.uint8)), 0)

    def test_preprocess_auto_rotates_sideways_only(self):
        upright = encode(text_page())
        sideways = encode(text_page().transpose(Image.Transpose.ROTATE_90))
        self.assertEqual(preprocess(upright).shape, (400, 600, 3))
        self.assertEqual(preprocess(sideways).shape, (400, 600, 3))

    def test_explicit_rotation_bypasses_estimator(self):
        sideways = encode(text_page().transpose(Image.Transpose.ROTATE_90))
        # Явные 180/270 применяются как есть, эвристика не вмешивается.
        self.assertEqual(preprocess(sideways, rotation=180).shape, (600, 400, 3))


class DeskewTests(unittest.TestCase):
    def test_corrects_thirty_degree_photo_and_maps_boxes_back(self):
        page = Image.new("RGB", (1000, 700), "white")
        draw = ImageDraw.Draw(page)
        for y in range(80, 650, 45):
            draw.line((80, y, 920, y), fill="black", width=3)
        rotated = page.rotate(30, resample=Image.Resampling.BICUBIC,
                              expand=True, fillcolor="white")

        prepared = prepare_image(encode(rotated))

        self.assertGreater(prepared.pixels.shape[1], prepared.pixels.shape[0])
        self.assertEqual(estimate_skew(cv2.cvtColor(prepared.pixels, cv2.COLOR_BGR2GRAY)), 0)
        bbox = prepared.original_bbox([0, 0, prepared.pixels.shape[1], prepared.pixels.shape[0]])
        self.assertGreater(bbox[2], bbox[0])
        self.assertGreater(bbox[3], bbox[1])
        self.assertLessEqual(bbox[2], prepared.width)
        self.assertLessEqual(bbox[3], prepared.height)


class PdfTests(unittest.TestCase):
    def test_pdf_first_page_rasterizes_to_pixels(self):
        from ml1.preprocess import prepare_image, rasterize_pdf_first_page
        page = Image.new("RGB", (200, 300), "white")
        stream = BytesIO()
        page.save(stream, format="PDF")
        pdf = stream.getvalue()
        self.assertTrue(pdf.startswith(b"%PDF-"))
        png = rasterize_pdf_first_page(pdf)
        self.assertTrue(png.startswith(b"\x89PNG"))
        prepared = prepare_image(pdf)
        self.assertEqual(prepared.pixels.ndim, 3)
        self.assertGreater(prepared.width, 0)

    def test_broken_pdf_is_rejected(self):
        from ml1.preprocess import prepare_image
        with self.assertRaises(ValueError):
            prepare_image(b"%PDF-broken")


if __name__ == "__main__":
    unittest.main()
