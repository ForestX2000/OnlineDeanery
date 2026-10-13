"""Decode document photos without erasing faint text or guessing their orientation."""

from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

# Порог уверенности для авто-поворота: боковое положение признаём, только если
# дисперсия профилей по столбцам явно выше, чем по строкам.
SIDEWAYS_RATIO = 1.5


def estimate_rotation(gray: np.ndarray) -> int:
    """Возвращает 90, если текст идёт вертикально (фото боком), иначе 0.

    Эвристика по проекционным профилям: у ровного текста строки чередуются
    «текст/пробел» (дисперсия построчных средних высокая), а столбцы похожи
    друг на друга. У повёрнутого на 90°/270° — наоборот. Дешёвая замена
    Tesseract OSD / angle classifier; 90° от 270° не отличает (возвращает 90),
    180° не детектирует. Явный параметр rotation в preprocess приоритетнее.
    """
    h, w = gray.shape[:2]
    scale = min(1.0, 800.0 / max(h, w))
    if scale < 1.0:
        small = cv2.resize(gray, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    else:
        small = gray
    # Только центр кадра: края фото (стол, фон) ломают профили (замер на
    # baton.png: весь кадр даёт col/row=22.4, центр 60% — 0.46; повёрнутый — 2.17).
    ch, cw = small.shape[:2]
    small = small[int(ch * 0.2):int(ch * 0.8), int(cw * 0.2):int(cw * 0.8)]
    if small.size == 0 or min(small.shape[:2]) < 8:
        return 0
    _, binary = cv2.threshold(small, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    ink = binary.astype(np.float32) / 255.0
    if ink.mean() < 0.005 or ink.mean() > 0.6:
        return 0
    row_var = float(ink.mean(axis=1).var())
    col_var = float(ink.mean(axis=0).var())
    if row_var <= 1e-9:
        return 0
    if col_var / row_var >= SIDEWAYS_RATIO:
        return 90
    return 0


@dataclass
class PreparedImage:
    pixels: np.ndarray
    width: int
    height: int
    rotation: int

    def metadata(self) -> dict:
        # The browser displays EXIF-corrected source pixels, not the OCR rotation.
        return {"width": self.width, "height": self.height, "rotation": self.rotation}

    def original_bbox(self, bbox: list[float]) -> list[float]:
        x1, y1, x2, y2 = bbox
        if self.rotation == 90:
            box = [y1, self.height - x2, y2, self.height - x1]
        elif self.rotation == 180:
            box = [self.width - x2, self.height - y2, self.width - x1, self.height - y1]
        elif self.rotation == 270:
            box = [self.width - y2, x1, self.width - y1, x2]
        else:
            box = bbox
        return [round(max(0.0, min(float(v), bound)), 2)
                for v, bound in zip(box, [self.width, self.height, self.width, self.height])]


def rasterize_pdf_first_page(pdf_bytes: bytes, dpi: int = 200) -> bytes:
    """Render page 0 of a PDF to PNG bytes (PyMuPDF); later pages are ignored."""
    import pymupdf
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as doc:
            if doc.is_encrypted or len(doc) == 0:
                raise ValueError("PDF защищён или не содержит страниц")
            page = doc[0]
            pix = page.get_pixmap(dpi=dpi)
            return pix.tobytes("png")
    except ValueError:
        raise
    except Exception as exc:
        raise ValueError("Не удалось растеризовать PDF") from exc


def prepare_image(image_bytes: bytes, rotation: int = 0) -> PreparedImage:
    """Return uint8 BGR pixels; apply clockwise rotation after EXIF orientation.
    White paper is not glare. Preserve the source resolution, colors, and strokes
    instead of applying inpainting, contrast normalization, or guessed deskew.
    rotation=0 включает авто-определение бокового фото (estimate_rotation);
    явные 90/180/270 применяются как есть и эвристику обходят.
    PDF растеризуется первой страницей (см. rasterize_pdf_first_page).
    """
    if type(rotation) is not int or rotation not in (0, 90, 180, 270):
        raise ValueError("Поворот должен быть 0, 90, 180 или 270 градусов")
    if image_bytes[:5] == b"%PDF-":
        # Кейс требует PDF: растеризуем первую страницу (остальные игнорируем).
        image_bytes = rasterize_pdf_first_page(image_bytes)

    try:
        with Image.open(BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source)
            if "A" in image.getbands() or "transparency" in image.info:
                rgba = image.convert("RGBA")
                background = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
                image = Image.alpha_composite(background, rgba).convert("RGB")
            else:
                image = image.convert("RGB")

            width, height = image.size

            rotations = {
                90: Image.Transpose.ROTATE_270,
                180: Image.Transpose.ROTATE_180,
                270: Image.Transpose.ROTATE_90,
            }
            if rotation == 0:
                gray = np.asarray(image.convert("L"))
                rotation = estimate_rotation(gray)
            if rotation:
                image = image.transpose(rotations[rotation])

            # OpenCV's PNG encoder (ml1.ocr) expects BGR, not Pillow's RGB.
            return PreparedImage(np.ascontiguousarray(np.asarray(image)[:, :, ::-1]),
                                 width, height, rotation)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("Не удалось декодировать изображение") from exc


def preprocess(image_bytes: bytes, rotation: int = 0) -> np.ndarray:
    """Backward-compatible decoder; geometry-aware callers use prepare_image."""
    return prepare_image(image_bytes, rotation).pixels
