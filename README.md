# Онлайн-деканат

Веб-приложение для вопросов о правилах деканата и проверки документов.

## Быстрый запуск через Docker

Нужен установленный и запущенный Docker Desktop с поддержкой `docker compose`.
Node.js и Python на компьютере устанавливать не нужно.

```powershell
git clone https://github.com/ForestX2000/OnlineDeanery.git
cd OnlineDeanery
docker compose up --build
```

После запуска откройте:

- Frontend: <http://localhost:5173>
- API и Swagger: <http://localhost:8000/docs>
- Сервис правил и Swagger: <http://localhost:8002/docs>
- Состояние сервиса правил: <http://localhost:8002/health>

Чтобы оставить контейнеры работающими в фоне, используйте
`docker compose up --build -d`. Посмотреть логи: `docker compose logs -f`.
Остановить и удалить контейнеры: `docker compose down`.

В форме можно сразу отправить вопрос **без файла**: Docker Compose запускает
frontend, API и сервис правил, и этот сценарий работает без дополнительных сервисов.

### Проверка документов

Одна команда поднимает все, включая OCR:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_llama.ps1
docker compose up --build
```

`install_llama.ps1` скачивает `llama-server` и оба `.gguf` в `./models/`.
Сервис OCR (`ml1`, PaddleOCR-VL через compose-сервис `llama`) и извлечение полей (`ml2`)
входят в репозиторий. Host-режим (`llama-server.exe` рядом) тоже поддерживается:
`PADDLEOCR_VL_URL=http://host.docker.internal:8080/v1/chat/completions`, см. `scripts/run_llama.ps1`.

- OCR: `http://localhost:8001/ocr` (в compose `ml1:8001` -> сервис `llama:8080`)
- Extract: `http://localhost:8003/extract` (в compose `ml2:8003`)
- llama-server: `http://localhost:8080/health` (модели из `./models/`, см. `models/README.md`)

PDF принимается API, но `ml1/preprocess` PDF не растеризует: для PDF используйте
JPG/PNG первой страницы, либо добавьте растеризацию (`pypdf/fitz/poppler`).
Без `YOLO_*.onnx` детектор возвращает `signature/stamp=null` («проверка не выполнена»).

Без `models/*.gguf` сервис `llama` будет перезапускаться, `ml1` вернет `503`.
Если адреса отличаются, создайте `.env` на основе `.env.example` и укажите
`PADDLEOCR_VL_URL`, `ML1_URL` и `ML2_URL`, затем перезапустите контейнеры:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Контракт интеграции и запуск без Docker описаны в [docs/api.md](docs/api.md).
