import argparse
import random
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import numpy as np


WIDTH, HEIGHT = 1240, 1754   # A4 @ 150 DPI
MARGIN = 80

FONT_PATH = None  # определится ниже


def get_font(size: int):
    """Arial с кириллицей или fallback."""
    for name in ("arial.ttf", "DejaVuSans.ttf", "LiberationSans-Regular.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def draw_centered(draw, text, y, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    x = (WIDTH - (bbox[2] - bbox[0])) // 2
    draw.text((x, y), text, fill="black", font=font)


def draw_line(draw, text, x, y, font, value=None):
    draw.text((x, y), text, fill="black", font=font)
    if value:
        bbox = draw.textbbox((x, y), text, font=font)
        draw.text((x + (bbox[2] - bbox[0]) + 10, y), value, fill="black", font=font)


def make_study_certificate(fio, vuz, program, form, period, number, date):
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    title_font = get_font(28)
    h_font = get_font(22)
    text_font = get_font(18)

    draw_centered(draw, "СПРАВКА ОБ ОБУЧЕНИИ", 60, title_font)
    draw_centered(draw, f"№ {number} от {date}", 100, text_font)

    y = 200
    for label, value in (
        ("ФИО студента:", fio),
        ("Название вуза:", vuz),
        ("Направление подготовки:", program),
        ("Форма обучения:", form),
        ("Период обучения:", period),
        ("Номер и дата выдачи:", f"{number} от {date}"),
    ):
        draw_line(draw, label, MARGIN, y, h_font, value)
        y += 60

    y += 60
    draw.text((MARGIN, y), "Подпись и печать:", fill="black", font=h_font)

    return img


def make_academic_leave(fio, group, course, reason, start, end, app_date):
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    title_font = get_font(28)
    h_font = get_font(22)
    text_font = get_font(18)

    draw_centered(draw, "ЗАЯВЛЕНИЕ", 60, title_font)
    draw_centered(draw, "на академический отпуск", 100, text_font)

    y = 200
    for label, value in (
        ("ФИО студента:", fio),
        ("Группа и курс:", f"{group}, {course} курс"),
        ("Причина отпуска:", reason),
        ("Дата начала отпуска:", start),
        ("Дата окончания отпуска:", end),
        ("Дата заявления:", app_date),
    ):
        draw_line(draw, label, MARGIN, y, h_font, value)
        y += 60

    y += 60
    draw.text((MARGIN, y), "Подпись студента:", fill="black", font=h_font)

    return img


def make_internship(fio, org, period, supervisor, grade, number, date):
    img = Image.new("RGB", (WIDTH, HEIGHT), "white")
    draw = ImageDraw.Draw(img)

    title_font = get_font(28)
    h_font = get_font(22)
    text_font = get_font(18)

    draw_centered(draw, "СПРАВКА О ПРАКТИКЕ", 60, title_font)
    draw_centered(draw, f"№ {number} от {date}", 100, text_font)

    y = 200
    for label, value in (
        ("ФИО студента:", fio),
        ("Организация:", org),
        ("Сроки практики:", period),
        ("Руководитель практики:", supervisor),
        ("Оценка:", grade),
        ("Номер и дата выдачи:", f"{number} от {date}"),
    ):
        draw_line(draw, label, MARGIN, y, h_font, value)
        y += 60

    y += 60
    draw.text((MARGIN, y), "Подпись и печать:", fill="black", font=h_font)

    return img


def draw_signature(img):
    """Простой росчерк."""
    draw = ImageDraw.Draw(img)
    x, y = MARGIN + 280, img.height - 350
    points = [(x, y)]
    for i in range(1, 12):
        points.append((x + i * 12, y + random.randint(-15, 15)))
    draw.line(points, fill="black", width=3)


def draw_stamp(img):
    """Синий круг с текстом."""
    draw = ImageDraw.Draw(img)
    cx, cy, r = img.width - 320, img.height - 280, 90
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(0, 0, 180), width=4)
    draw.ellipse([cx - r + 12, cy - r + 12, cx + r - 12, cy + r - 12],
                 outline=(0, 0, 180), width=2)
    font = get_font(20)
    text = "МГУ"
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text((cx - (bbox[2] - bbox[0]) // 2, cy - 10), text,
              fill=(0, 0, 180), font=font)


# ==== Условия съёмки ====

def apply_rotation(img, angle):
    return img.rotate(angle, expand=True, fillcolor="white",
                      resample=Image.BICUBIC)


def apply_shadow(img):
    """Затемнение с одной стороны."""
    arr = np.array(img).astype(np.float32)
    h, w = arr.shape[:2]
    gradient = np.linspace(0.55, 1.0, w).reshape(1, w, 1)
    arr = arr * gradient
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def apply_glare(img):
    """Яркое пятно."""
    arr = np.array(img).astype(np.float32)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy = w // 3, h // 4
    dist2 = (xx - cx) ** 2 + (yy - cy) ** 2
    glare = 1.0 + 0.8 * np.exp(-dist2 / (2 * (w // 4) ** 2))
    arr = arr * glare.reshape(h, w, 1)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def apply_low_res(img):
    small = img.resize((img.width // 3, img.height // 3), Image.BILINEAR)
    return small.resize(img.size, Image.BILINEAR)


def apply_blur(img):
    return img.filter(ImageFilter.GaussianBlur(radius=1.5))


# ==== Генерация вариантов ====

def save_variants(img, out_dir, prefix, with_signature, with_stamp):
    """Сохраняет документ в разных условиях."""
    out_dir.mkdir(parents=True, exist_ok=True)

    if with_signature:
        draw_signature(img)
    if with_stamp:
        draw_stamp(img)

    variants = {
        "clean": lambda i: i,
        "skew15": lambda i: apply_rotation(i, -15),
        "skew30": lambda i: apply_rotation(i, -30),
        "shadow": apply_shadow,
        "glare": apply_glare,
        "lowres": apply_low_res,
        "blur": apply_blur,
        "rot90": lambda i: i.rotate(90, expand=True),
        "rot180": lambda i: i.rotate(180, expand=True),
    }

    for name, transform in variants.items():
        out = transform(img)
        out.save(out_dir / f"{prefix}_{name}.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="demo_docs", help="Папка для выходных файлов")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    random.seed(42)

    # ==== Справка об обучении ====
    cert = make_study_certificate(
        fio="Иванов Иван Иванович",
        vuz="МГУ имени М.В. Ломоносова",
        program="Прикладная математика и информатика",
        form="очная",
        period="02.09.2022 – 30.06.2026",
        number="12345",
        date="10.10.2025",
    )
    save_variants(cert, out / "study_certificate", "study", True, True)

    # ==== Заявление на академотпуск ====
    leave = make_academic_leave(
        fio="Петрова Мария Сергеевна",
        group="ПМ-21",
        course=2,
        reason="по состоянию здоровья",
        start="01.11.2025",
        end="31.03.2026",
        app_date="15.10.2025",
    )
    save_variants(leave, out / "academic_leave", "leave", True, False)

    # ==== Справка о практике ====
    practice = make_internship(
        fio="Сидоров Алексей Петрович",
        org="ООО «ТехноПарк»",
        period="01.07.2025 – 31.08.2025",
        supervisor="Смирнов А.А.",
        grade="отлично",
        number="54321",
        date="05.09.2025",
    )
    save_variants(practice, out / "internship_certificate", "practice", True, True)

    # ==== Без подписи/печати (проверка incomplete) ====
    cert_no = make_study_certificate(
        fio="Иванов Иван Иванович",
        vuz="МГУ имени М.В. Ломоносова",
        program="Прикладная математика и информатика",
        form="очная",
        period="02.09.2022 – 30.06.2026",
        number="12345",
        date="10.10.2025",
    )
    save_variants(cert_no, out / "study_certificate_no_marks", "study_nomarks",
                  False, False)

    print(f"Готово. Документы в: {out}")
    print("\nСтруктура:")
    for folder in sorted(out.iterdir()):
        if folder.is_dir():
            count = len(list(folder.glob("*.png")))
            print(f"  {folder.name}/ — {count} файлов")


if __name__ == "__main__":
    main()