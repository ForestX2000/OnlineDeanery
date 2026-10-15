"""Прогон синтетических документов через /analyze и отчёт.

Использование:
    python tools/run_demo_eval.py --docs demo_docs --api-url http://localhost:8000
"""

import argparse
import json
import time
from pathlib import Path

import requests


# ==== Эталоны для проверки ====
EXPECTED = {
    "study_certificate": {
        "document_type": "study_certificate",
        "fields": {
            "student_name": "Иванов Иван Иванович",
            "university": "МГУ",
            "program": "Прикладная математика",
            "study_form": "очная",
            "study_period": "02.09.2022",
            "document_number": "12345",
            "issue_date": "10.10.2025",
            "signature": True,
            "stamp": True,
        },
    },
    "academic_leave": {
        "document_type": "academic_leave",
        "fields": {
            "student_name": "Петрова Мария Сергеевна",
            "group": "ПМ-21",
            "reason": "здоров",
            "start_date": "01.11.2025",
            "end_date": "31.03.2026",
            "application_date": "15.10.2025",
            "signature": True,
        },
    },
    "internship_certificate": {
        "document_type": "internship_certificate",
        "fields": {
            "student_name": "Сидоров Алексей Петрович",
            "organization": "ТехноПарк",
            "internship_period": "01.07.2025",
            "supervisor": "Смирнов",
            "grade": "отлично",
            "document_number": "54321",
            "issue_date": "05.09.2025",
            "signature": True,
            "stamp": True,
        },
    },
}


def run_one(api_url: str, image_path: Path, question: str,
            doc_type: str | None = None) -> dict:
    """Отправляет один документ на /analyze, возвращает распарсенный ответ."""
    data = {"question": question}
    if doc_type:
        data["document_type"] = doc_type

    with image_path.open("rb") as f:
        files = {"file": (image_path.name, f, "image/png")}
        t0 = time.time()
        resp = requests.post(f"{api_url}/analyze", data=data, files=files,
                             timeout=300)
        dt = time.time() - t0

    if resp.status_code != 200:
        return {
            "status_code": resp.status_code,
            "error": resp.text[:500],
            "elapsed": round(dt, 2),
        }

    result = resp.json()
    result["_elapsed"] = round(dt, 2)
    return result


def field_matches(expected: str, actual: str) -> bool:
    """Мягкое сравнение: подстрока или частичное совпадение."""
    if not actual or actual == "не найдено":
        return False
    exp_low = expected.lower()
    act_low = str(actual).lower()
    # одна строка содержится в другой
    if exp_low in act_low or act_low in exp_low:
        return True
    # совпадение по первым 4 символам (для опечаток OCR)
    if len(exp_low) >= 4 and exp_low[:4] in act_low:
        return True
    return False


def evaluate(api_url: str, docs_dir: Path, out_json: Path, out_md: Path):
    """Прогоняет все документы, считает метрики, пишет отчёты."""
    results = []
    total = 0
    type_ok = 0
    field_ok = 0
    field_total = 0
    errors = 0

    # Каждая подпапка — тип документа
    folders = [d for d in sorted(docs_dir.iterdir()) if d.is_dir()]

    for folder in folders:
        # Определяем базовый тип (отрезаем суффиксы вроде _no_marks)
        base_type = None
        for key in EXPECTED:
            if folder.name.startswith(key):
                base_type = key
                break
        if base_type is None:
            continue

        expected = EXPECTED[base_type]
        # Если папка _no_marks — подписи/печати нет
        expect_marks = not folder.name.endswith("_no_marks")

        images = sorted(folder.glob("*.png"))
        print(f"\n=== {folder.name} ({len(images)} файлов) ===")

        for img in images:
            total += 1
            print(f"  [{total}] {img.name}...", end=" ", flush=True)

            response = run_one(api_url, img, "Хватит ли этого документа?",
                               doc_type=None)

            if "error" in response:
                errors += 1
                print(f"ERROR {response['status_code']}: {response['error'][:80]}")
                results.append({
                    "file": str(img.relative_to(docs_dir)),
                    "expected_type": base_type,
                    "error": response["error"],
                    "status_code": response["status_code"],
                    "elapsed": response["elapsed"],
                })
                continue

            doc = response.get("document") or {}
            got_type = doc.get("type")
            got_fields = doc.get("fields") or {}
            verification = response.get("verification") or {}
            elapsed = response.get("_elapsed", 0)

            # Проверка типа
            type_match = (got_type == expected["document_type"])
            if type_match:
                type_ok += 1

            # Проверка полей
            field_results = {}
            for fname, fvalue in expected["fields"].items():
                # Если ждём False для signature/stamp (no_marks)
                if fname in ("signature", "stamp") and not expect_marks:
                    expected_val = False
                else:
                    expected_val = fvalue

                actual = got_fields.get(fname)
                field_total += 1

                if isinstance(expected_val, bool):
                    # Для boolean сравниваем строго
                    ok = (actual is expected_val)
                else:
                    ok = field_matches(str(expected_val), str(actual))

                if ok:
                    field_ok += 1

                field_results[fname] = {
                    "expected": expected_val,
                    "actual": actual,
                    "ok": ok,
                }

            status_icon = "✅" if type_match else "❌"
            print(f"{status_icon} type={got_type} "
                  f"fields={sum(1 for f in field_results.values() if f['ok'])}/"
                  f"{len(field_results)} "
                  f"verify={verification.get('status')} "
                  f"{elapsed}s")

            results.append({
                "file": str(img.relative_to(docs_dir)),
                "expected_type": base_type,
                "got_type": got_type,
                "type_ok": type_match,
                "expected_fields": expected["fields"],
                "got_fields": got_fields,
                "field_results": field_results,
                "verification": verification,
                "answer": response.get("answer", "")[:300],
                "sources": response.get("sources", []),
                "elapsed": elapsed,
            })

    # ==== Итоги ====
    summary = {
        "total": total,
        "errors": errors,
        "type_accuracy": round(type_ok / total, 3) if total else 0,
        "field_accuracy": round(field_ok / field_total, 3) if field_total else 0,
        "fields_ok": field_ok,
        "fields_total": field_total,
    }

    print("\n=== ИТОГИ ===")
    print(f"Всего: {total}")
    print(f"Ошибок: {errors}")
    print(f"Точность типа: {summary['type_accuracy']:.1%}")
    print(f"Точность полей: {summary['field_accuracy']:.1%} "
          f"({field_ok}/{field_total})")

    # ==== JSON-отчёт ====
    out_json.parent.mkdir(parents=True, exist_ok=True)
    with out_json.open("w", encoding="utf-8") as f:
        json.dump({"summary": summary, "results": results}, f,
                  ensure_ascii=False, indent=2)
    print(f"\nJSON-отчёт: {out_json}")

    # ==== Markdown-отчёт ====
    with out_md.open("w", encoding="utf-8") as f:
        f.write("# Отчёт по синтетическим документам\n\n")
        f.write(f"- Всего: **{total}**\n")
        f.write(f"- Ошибок: **{errors}**\n")
        f.write(f"- Точность типа: **{summary['type_accuracy']:.1%}**\n")
        f.write(f"- Точность полей: **{summary['field_accuracy']:.1%}** "
                f"({field_ok}/{field_total})\n\n")

        for r in results:
            f.write(f"## `{r['file']}`\n\n")
            if "error" in r:
                f.write(f"**ОШИБКА**: {r['error']}\n\n")
                continue
            f.write(f"- Ожидаемый тип: `{r['expected_type']}`\n")
            f.write(f"- Полученный тип: `{r['got_type']}` "
                    f"{'✅' if r['type_ok'] else '❌'}\n")
            f.write(f"- Проверка: `{r['verification'].get('status')}`\n")
            f.write(f"- Время: {r['elapsed']}с\n\n")

            f.write("| Поле | Ожидалось | Получено | OK |\n")
            f.write("|------|-----------|----------|----|\n")
            for fname, fr in r["field_results"].items():
                icon = "✅" if fr["ok"] else "❌"
                exp = str(fr["expected"])[:50]
                act = str(fr["actual"])[:50]
                f.write(f"| `{fname}` | {exp} | {act} | {icon} |\n")
            f.write("\n")

            if r.get("answer"):
                f.write(f"**Ответ**: {r['answer'][:200]}...\n\n")
            f.write("---\n\n")

    print(f"Markdown-отчёт: {out_md}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", default="demo_docs")
    parser.add_argument("--api-url", default="http://localhost:8000")
    parser.add_argument("--out-json", default="demo_eval.json")
    parser.add_argument("--out-md", default="demo_eval.md")
    args = parser.parse_args()

    evaluate(args.api_url, Path(args.docs),
             Path(args.out_json), Path(args.out_md))


if __name__ == "__main__":
    main()