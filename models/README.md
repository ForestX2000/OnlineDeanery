# Модели llama-server (не в git, только .gitkeep)

Для одной команды `docker compose up --build` положите сюда 2 файла (~1-2 ГБ):

- `PaddleOCR-VL-1.5.gguf`
- `PaddleOCR-VL-1.5-mmproj.gguf`

Источник: HuggingFace `PaddlePaddle/PaddleOCR-VL-1.5-GGUF`.

Быстро (PowerShell, из корня репо):

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_llama.ps1
```

Вручную: скачайте оба файла со страницы релиза и положите в `./models/`.

Без этих файлов сервис `llama` будет перезапускаться, а `ml1` вернет
`503 OCR-модель недоступна` — вопросы без файла при этом работают.

## Детектор подписей

`models/signature.onnx` (36 МБ, в git не входит) — экспорт Mels22 YOLO11s 4cls:

```powershell
Invoke-WebRequest -Uri https://huggingface.co/Mels22/Signature-Detection-Verification/resolve/main/detector_yolo_4cls.pt -OutFile models/sig4cls.pt
.venv/Scripts/python.exe -c "from ultralytics import YOLO; YOLO('models/sig4cls.pt').export(format='onnx', imgsz=640, batch=1, dynamic=False, half=False, simplify=True, opset=17, nms=False)"
Move-Item models/sig4cls.onnx models/signature.onnx -Force
```

Печать ищется классикой синего кольца без весов (`YOLO_STAMP_HEURISTIC=1`).
Свою YOLO-печать можно подсунуть через `YOLO_MODEL_PATH` — она приоритетнее.
