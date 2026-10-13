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
