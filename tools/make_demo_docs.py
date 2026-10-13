"""Синтетические демо-документы (академ-отпуск, практика) для видео и results.json.

Шаблоны заточены под regex ml2/extract.py. Подпись — росчерк (для YOLO),
печать — синее кольцо (для классики). Запуск из корня репо:
  python -m tools.make_demo_docs --output ./demo_docs
"""
from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


def font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        Path("C:/Windows/Fonts/arial.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def squiggle(draw: ImageDraw.ImageDraw, x0: int, y0: int) -> None:
    pts = [(x0 + i * 9, y0 + (7 if i % 2 == 0 else -7) + i) for i in range(14)]
    draw.line(pts, fill=(20, 20, 120), width=3, joint="curve")


def blue_ring(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int) -> None:
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(40, 90, 200), width=6)
    draw.ellipse([cx - r + 16, cy - r + 16, cx + r - 16, cy + r - 16],
                 outline=(40, 90, 200), width=3)


LEAVE_LINES = [
    "ЗАЯВЛЕНИЕ",
    "на академический отпуск",
    "",
    "ФИО: Петров Пётр Петрович",
    "Группа: ИВТ-21, 2 курс",
    "Причина отпуска: по болезни",
    "Дата начала отпуска: 01.09.2026",
    "Дата окончания отпуска: 01.09.2027",
    "Дата заявления: 20.08.2026",
]

PRACTICE_LINES = [
    "СПРАВКА о прохождении практики",
    "",
    "ФИО: Сидорова Анна Ивановна",
    "Организация: «Рога и копыта»",
    "Сроки практики: с 01.06.2026 по 30.06.2026",
    "Руководитель практики: Петров П.П.",
    "Оценка: отлично",
    "Дата выдачи: 01.07.2026, № 77",
]


def render(lines: list[str], path: Path) -> None:
    face, small = font(34), font(26)
    page = Image.new("RGB", (1200, 1500), "white")
    draw = ImageDraw.Draw(page)
    y = 90
    for line in lines:
        draw.text((90, y), line or " ", fill=(10, 10, 10), font=face)
        y += 62
    squiggle(draw, 150, y + 40)
    draw.text((150, y + 130), "Подпись студента", fill=(10, 10, 10), font=small)
    blue_ring(draw, 880, y + 120, 110)
    page.save(path)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", default="demo_docs")
    args = ap.parse_args()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    render(LEAVE_LINES, out / "academic_leave.png")
    render(PRACTICE_LINES, out / "internship_certificate.png")
    print(f"saved to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
