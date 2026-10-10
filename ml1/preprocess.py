import cv2
import numpy as np


# выравнивает наклон изображения до 30 градусов
def deskew(image: np.ndarray, max_angle: float = 30.0) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(gray, 0, 255,
                           cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    coords = np.column_stack(np.where(thresh > 0))
    if len(coords) < 100:
        return image

    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = 90 + angle
    angle = max(-max_angle, min(max_angle, angle))

    if abs(angle) < 0.5:
        return image

    h, w = image.shape[:2]
    m = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    return cv2.warpAffine(image, m, (w, h),
                          flags=cv2.INTER_CUBIC,
                          borderMode=cv2.BORDER_REPLICATE)


# убирает тени через дилатацию и медианный фильтр
def remove_shadows(image: np.ndarray) -> np.ndarray:
    planes = cv2.split(image)
    result = []
    for plane in planes:
        dilated = cv2.dilate(plane, np.ones((7, 7), np.uint8))
        bg = cv2.medianBlur(dilated, 21)
        diff = 255 - cv2.absdiff(plane, bg)
        norm = cv2.normalize(diff, None, alpha=0, beta=255,
                             norm_type=cv2.NORM_MINMAX,
                             dtype=cv2.CV_8UC1)
        result.append(norm)
    return cv2.merge(result)


# убирает блики через inpaint по маске ярких пятен
def remove_glare(image: np.ndarray, threshold: int = 240) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    mask = cv2.dilate(mask, np.ones((5, 5), np.uint8), iterations=2)
    if mask.sum() == 0:
        return image
    return cv2.inpaint(image, mask, 3, cv2.INPAINT_TELEA)


# апскейлит изображение, если короткая сторона меньше min_side
def upscale_if_small(image: np.ndarray, min_side: int = 1000) -> np.ndarray:
    h, w = image.shape[:2]
    short = min(h, w)
    if short >= min_side:
        return image
    scale = min_side / short
    return cv2.resize(image, (int(w * scale), int(h * scale)),
                      interpolation=cv2.INTER_CUBIC)


# вытягивает контраст через CLAHE по L-каналу LAB
def enhance_contrast(image: np.ndarray) -> np.ndarray:
    lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    return cv2.cvtColor(cv2.merge([l, a, b]), cv2.COLOR_LAB2BGR)


# полный пайплайн: decode → upscale → deskew → glare → shadows → contrast
def preprocess(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError("Не удалось декодировать изображение")

    img = upscale_if_small(img)
    img = deskew(img)
    img = remove_glare(img)
    img = remove_shadows(img)
    img = enhance_contrast(img)
    return img