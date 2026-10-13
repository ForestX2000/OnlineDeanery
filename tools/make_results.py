"""Генерация results.json для закрытой проверки через POST /analyze.

Формат входа: папка с файлами + questions.json:
  questions.json = [{"id": "doc1", "file": "doc1.jpg", "question": "...", "document_type": "study_certificate"|null}, ...]
Поддерживаются .json (список) и .jsonl (по объекту на строку).

Выход results.json: [{"id":..., "document": {"type":..., "fields": {...}}, "answer": "...", "sources": [...], "verification": {...}}, ...]
Ошибки HTTP фиксируются как {"id":..., "error": "502: ..."} чтобы автопроверка видела пропуски.

Пример:
  python -m tools.make_results --input ./closed --output results.json --api-url http://localhost:8000
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path


def load_questions(path: Path) -> list[dict]:
    if path.suffix == ".jsonl":
        items = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line:
                items.append(json.loads(line))
        return items
    return json.loads(path.read_text(encoding="utf-8"))


def encode_multipart(fields: dict[str, str], file_field: str, file_path: Path) -> tuple[bytes, str]:
    boundary = "----deanery%08x" % (int(time.time() * 1000) % 0xFFFFFFFF)
    buf = bytearray()
    for key, value in fields.items():
        buf += f"--{boundary}\r\n".encode()
        buf += f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode()
        buf += f"{value}\r\n".encode()
    mime, _ = mimetypes.guess_type(str(file_path))
    mime = mime or "application/octet-stream"
    data = file_path.read_bytes()
    buf += f"--{boundary}\r\n".encode()
    buf += f'Content-Disposition: form-data; name="{file_field}"; filename="{file_path.name}"\r\n'.encode()
    buf += f"Content-Type: {mime}\r\n\r\n".encode()
    buf += data + b"\r\n"
    buf += f"--{boundary}--\r\n".encode()
    return bytes(buf), f"multipart/form-data; boundary={boundary}"


def post_analyze(api_url: str, file_path: Path, question: str, document_type: str | None, timeout: int) -> dict:
    fields: dict[str, str] = {"question": question}
    if document_type:
        fields["document_type"] = document_type
    body, ctype = encode_multipart(fields, "file", file_path)
    req = urllib.request.Request(f"{api_url.rstrip('/')}/analyze", data=body,
                                 headers={"Content-Type": ctype}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return {"ok": True, "payload": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as exc:
        try:
            detail = exc.read().decode("utf-8", "replace")[:500]
        except Exception:
            detail = ""
        return {"ok": False, "error": f"{exc.code}: {detail}"}
    except Exception as exc:
        return {"ok": False, "error": f"request failed: {exc}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", required=True, help="Папка с файлами и questions.json/.jsonl")
    ap.add_argument("--questions", default="questions.json", help="Имя файла вопросов внутри --input")
    ap.add_argument("--output", default="results.json")
    ap.add_argument("--api-url", default="http://localhost:8000")
    ap.add_argument("--timeout", type=int, default=200)
    args = ap.parse_args()

    indir = Path(args.input)
    qpath = indir / args.questions
    if not qpath.exists():
        # allow --questions as full path
        qpath = Path(args.questions)
    items = load_questions(qpath)
    results = []
    for it in items:
        doc_id = str(it.get("id", Path(it.get("file", "")).stem))
        rel = it.get("file", "")
        fpath = (indir / rel) if rel else None
        question = it.get("question", "")
        dtype = it.get("document_type")
        if not fpath or not fpath.exists():
            results.append({"id": doc_id, "error": f"file not found: {rel}"})
            print(f"[SKIP] {doc_id}: нет файла {rel}", file=sys.stderr)
            continue
        print(f"[POST] {doc_id} {fpath.name} ...", flush=True)
        res = post_analyze(args.api_url, fpath, question, dtype, args.timeout)
        if not res["ok"]:
            results.append({"id": doc_id, "error": res["error"]})
            print(f"[FAIL] {doc_id}: {res['error']}", file=sys.stderr)
            continue
        p = res["payload"]
        doc = p.get("document") or {}
        results.append({
            "id": doc_id,
            "document": {"type": doc.get("type"), "fields": doc.get("fields", {})},
            "answer": p.get("answer", ""),
            "sources": p.get("sources", []),
            "verification": p.get("verification"),
            "conversation_id": p.get("conversation_id"),
        })
        print(f"[OK] {doc_id}", flush=True)

    Path(args.output).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved {len(results)} -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
