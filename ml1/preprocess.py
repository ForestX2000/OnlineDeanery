"""Decode document photos without erasing faint text or guessing their orientation."""

from dataclasses import dataclass
from io import BytesIO

import cv2
import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError

# Порог уверенности для авто-поворота: боковое положение признаём, только если
# дисперсия профилей по столбцам явно выше, чем по строкам.
SIDEWAYS_RATIO = 1.5
MIN_DESKEW_ANGLE = 6.0
MAX_DESKEW_ANGLE = 35.0


def estimate_skew(gray: np.ndarray) -> float:
    """Estimate dominant text-line skew in degrees; return 0 when uncertain."""
    height, width = gray.shape[:2]
    scale = min(1.0, 1000.0 / max(height, width))
    if scale < 1.0:
        gray = cv2.resize(gray, (int(width * scale), int(height * scale)),
                          interpolation=cv2.INTER_AREA)
    height, width = gray.shape[:2]
    region = gray[int(height * 0.15):int(height * 0.85),
                  int(width * 0.15):int(width * 0.85)]
    if min(region.shape[:2]) < 80:
        return 0.0

    edges = cv2.Canny(region, 50, 150, apertureSize=3)
    min_length = max(30, int(min(height, width) * 0.06))
    lines = cv2.HoughLinesP(edges, 1, np.pi / 360, threshold=70,
                            minLineLength=min_length, maxLineGap=25)
    if lines is None:
        return 0.0

    angles: list[tuple[float, float]] = []
    for x1, y1, x2, y2 in lines.reshape(-1, 4):
        length = float(np.hypot(x2 - x1, y2 - y1))
        angle = float(np.degrees(np.arctan2(y2 - y1, x2 - x1)))
        if (MIN_DESKEW_ANGLE / 2 <= abs(angle) <= MAX_DESKEW_ANGLE
                and min_length <= length < width * 0.65):
            angles.append((angle, length))
    if not angles:
        return 0.0

    # Group nearby line angles. A clear cluster avoids following table grain,
    # page edges, or a few isolated marks instead of the text baselines.
    bins: dict[int, float] = {}
    for angle, length in angles:
        key = round(angle)
        bins[key] = bins.get(key, 0.0) + length
    dominant = max(bins, key=bins.get)
    cluster = [(angle, length) for angle, length in angles
               if abs(angle - dominant) <= 2.0]
    cluster_weight = sum(length for _, length in cluster)
    total_weight = sum(length for _, length in angles)
    if cluster_weight < max(1200.0, min(height, width) * 4.0):
        return 0.0
    if cluster_weight / max(total_weight, 1.0) < 0.45:
        return 0.0
    estimate = sum(angle * length for angle, length in cluster) / cluster_weight
    return estimate if abs(estimate) >= MIN_DESKEW_ANGLE else 0.0


def deskew(image: np.ndarray) -> tuple[np.ndarray, np.ndarray | None, tuple[int, int]]:
    """Rotate a confidently skewed page to horizontal, preserving the full frame."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    skew = estimate_skew(gray)
    if not skew:
        return image, None, (0, 0)

    height, width = image.shape[:2]
    radians = np.deg2rad(-skew)
    new_width = int(height * abs(np.sin(radians)) + width * abs(np.cos(radians)))
    new_height = int(height * abs(np.cos(radians)) + width * abs(np.sin(radians)))
    # In image coordinates a positive Hough angle points downwards; OpenCV's
    # affine rotation changes that angle in the opposite direction.
    transform = cv2.getRotationMatrix2D((width / 2.0, height / 2.0), skew, 1.0)
    transform[0, 2] += new_width / 2.0 - width / 2.0
    transform[1, 2] += new_height / 2.0 - height / 2.0
    corrected = cv2.warpAffine(image, transform, (new_width, new_height),
                               flags=cv2.INTER_CUBIC,
                               borderMode=cv2.BORDER_CONSTANT,
                               borderValue=(255, 255, 255))
    # Deskewing an already rotated photo adds a large white canvas. Crop that
    # canvas back to the photographed frame so OCR keeps the same text scale.
    content = cv2.threshold(cv2.cvtColor(corrected, cv2.COLOR_BGR2GRAY), 245, 255,
                            cv2.THRESH_BINARY_INV)[1]
    points = cv2.findNonZero(content)
    offset = (0, 0)
    if points is not None:
        x, y, crop_width, crop_height = cv2.boundingRect(points)
        padding = max(4, int(min(height, width) * 0.006))
        left, top = max(0, x - padding), max(0, y - padding)
        right = min(new_width, x + crop_width + padding)
        bottom = min(new_height, y + crop_height + padding)
        crop_area = (right - left) * (bottom - top)
        if crop_area < new_width * new_height * 0.92:
            corrected = corrected[top:bottom, left:right]
            offset = (left, top)
    return corrected, transform, offset


def enhance_for_ocr(image: np.ndarray) -> np.ndarray:
    """Gently normalize local contrast while retaining color for stamp detection."""
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    lightness, a_channel, b_channel = cv2.split(lab)
    lightness = cv2.createCLAHE(clipLimit=1.5, tileGridSize=(8, 8)).apply(lightness)
    blurred = cv2.GaussianBlur(lightness, (0, 0), 0.8)
    lightness = cv2.addWeighted(lightness, 1.12, blurred, -0.12, 0)
    return cv2.cvtColor(cv2.merge((lightness, a_channel, b_channel)), cv2.COLOR_LAB2BGR)


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
    deskew_transform: np.ndarray | None = None
    deskew_crop_offset: tuple[int, int] = (0, 0)
    ocr_pixels: np.ndarray | None = None

    def metadata(self) -> dict:
        # The browser displays EXIF-corrected source pixels, not the OCR rotation.
        return {"width": self.width, "height": self.height, "rotation": self.rotation}

    def original_bbox(self, bbox: list[float]) -> list[float]:
        x1, y1, x2, y2 = bbox
        points = np.array([[x1, y1], [x2, y1], [x2, y2], [x1, y2]], dtype=np.float32)
        points[:, 0] += self.deskew_crop_offset[0]
        points[:, 1] += self.deskew_crop_offset[1]
        if self.deskew_transform is not None:
            inverse = cv2.invertAffineTransform(self.deskew_transform)
            points = cv2.transform(points[None, ...], inverse)[0]
        if self.rotation == 90:
            points = np.column_stack((points[:, 1], self.height - points[:, 0]))
        elif self.rotation == 180:
            points = np.column_stack((self.width - points[:, 0], self.height - points[:, 1]))
        elif self.rotation == 270:
            points = np.column_stack((self.width - points[:, 1], points[:, 0]))
        box = [points[:, 0].min(), points[:, 1].min(),
               points[:, 0].max(), points[:, 1].max()]
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
    and applies restrained local contrast to a separate OCR copy.
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
            pixels = np.ascontiguousarray(np.asarray(image)[:, :, ::-1])
            pixels, deskew_transform, deskew_crop_offset = deskew(pixels)
            ocr_pixels = enhance_for_ocr(pixels)
            return PreparedImage(pixels, width, height, rotation, deskew_transform,
                                 deskew_crop_offset, ocr_pixels)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise ValueError("Не удалось декодировать изображение") from exc


def preprocess(image_bytes: bytes, rotation: int = 0) -> np.ndarray:
    """Backward-compatible decoder; geometry-aware callers use prepare_image."""
    return prepare_image(image_bytes, rotation).pixels
