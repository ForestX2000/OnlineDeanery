# Онлайн-деканат

Цифровой секретарь: читает фото студенческого документа (OCR), заполняет карточку полей и отвечает на вопрос со ссылкой на пункты правил.
Пайплайн: распознать текст → разложить данные по полям → ответить со ссылкой.

Всё работает локально, внешние LLM API не используются.

## Публичный деплой

Проект уже развёрнут и доступен без установки: <https://deanery.forestinc.ru/>

Можно открыть ссылку и попробовать загружать документы и задавать вопросы. Вход для администратора: `admin@university.ru` / `admin12345678`. Если нужно развернуть свою копию — см. раздел «Быстрый старт: Docker Compose».

## Содержание

- [Быстрый старт: Docker Compose (рекомендуется)](#быстрый-старт-docker-compose)
- [Запуск без Docker (локально)](#запуск-без-докера-локально)
- [Адреса сервисов после запуска](#адреса-сервисов-после-запуска)
- [Аккаунты и безопасность](#аккаунты-и-безопасность)
- [Как пользоваться](#как-пользоваться)
- [Пакетная проверка results.json](#пакетная-проверка-resultsjson)
- [Тесты](#тесты)
- [Полезные команды](#полезные-команды)
- [Стек и инструменты](#стек-и-инструменты)
- [Документация](#документация)

## Быстрый старт: Docker Compose (рекомендуется)

Нужен установленный и запущенный Docker Desktop с поддержкой `docker compose`. Node.js и Python на компьютере устанавливать не нужно — все сервисы собираются из образов.

### 1. Клонируйте репозиторий

```powershell
git clone https://github.com/ForestX2000/OnlineDeanery.git
cd OnlineDeanery
```

### 2. Создайте файл `.env`

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Обязательно отредактируйте `.env`:

- `POSTGRES_PASSWORD` — случайный URL-safe секрет не короче 32 символов. Без него compose не запустит базу. Не используйте пароль из примера и не коммитьте `.env` (уже добавлен в `.gitignore`).
- По желанию, **до первого запуска**: `BOOTSTRAP_ADMIN_EMAIL` и `BOOTSTRAP_ADMIN_PASSWORD` (от 8 символов) — создать bootstrap-администратора. Если не задать, сервисы запустятся без начального администратора; загрузка и обработка документов останутся доступны.

Пример:

```
BOOTSTRAP_ADMIN_EMAIL=admin@university.ru
BOOTSTRAP_ADMIN_PASSWORD=admin12345678
BOOTSTRAP_ADMIN_NAME=Алексей Админов
```

Для доступа фронтенда к бэкенду укажите `VITE_API_URL=http://localhost:8000` (для локального запуска).

### 3. Скачайте модели OCR (~1,8 ГБ)

Модели не входят в git (см. `.gitignore` и `models/README.md`). Из корня репозитория:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_llama.ps1
```

Скрипт скачает `llama-server.exe` (в `C:\llama`) и два `.gguf` файла модели PaddleOCR-VL-1.6 (веса и мультимодальный проектор `-mmproj`) в `./models/`. Точные имена файлов смотрите в `models/README.md`.

Без этих файлов сервис `llama` будет перезапускаться, а `ml1` вернёт `503` — вопросы без файла при этом продолжают работать.

#### Детектор подписи и печати (опционально)

В папке `./models/` уже лежат `signature.onnx` (подпись) и `detector_yolo_4cls.pt`. Если скачали RF-DETR модель (`best.pth` + `config.json` от `ducln-business/document-signature-stamp-detector-v20`), положите их рядом:

```
models/best.pth
models/config.json
```

И раскомментируйте в `.env`:

```
RFDETR_MODEL_PATH=/models/best.pth
RFDETR_CONFIG_PATH=/models/config.json
RFDETR_CONFIDENCE=0.3
```

RF-DETR требует пакет `rfdetr` (и `torch`): `pip install rfdetr torch`. Без них сервис `ml1` проигнорирует RF-DETR и использует остальные источники (YOLO ONNX / цветовой поиск печати).

### 4. Запустите все сервисы

```powershell
docker compose up --build -d
```

Первый запуск может занять несколько минут: сборка образов и загрузка модели в `llama`.

### 5. Откройте в браузере

- Frontend: <http://localhost:5173>
- API и Swagger: <http://localhost:8000/docs>, здоровье: <http://localhost:8000/health>
- Сервис правил и Swagger: <http://localhost:8002/docs>, здоровье: <http://localhost:8002/health>

Вопрос **без файла** работает сразу (frontend + API + правила). С файлом нужны `ml1` (OCR) и `ml2` (поля); без `models/*.gguf` сервис `llama` перезапускается, `ml1` вернёт `503`.

## Запуск без Docker (локально)

Понадобятся: Python 3.10+, Node.js 22+, для `ml1` — установленный Tesseract OCR с файлами `rus.traineddata` и `osd.traineddata` (переменная `TESSDATA_PREFIX`).

Все команды — PowerShell из корня репозитория.

### 1. Бэкенд API (порт 8000)

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
.venv/Scripts/python.exe -m uvicorn backend.api:app --reload --host 127.0.0.1 --port 8000
```

Для личного кабинета/админки поднимите PostgreSQL (например, только сервис `db` через `docker compose up -d db`) и задайте `DATABASE_URL`; иначе API работает без БД. Применение миграций:

```powershell
.venv/Scripts/python.exe -m backend.init_db
.venv/Scripts/python.exe -m backend.seed
```

### 2. Backend 2 / правила (порт 8002) — второй терминал

```powershell
.venv/Scripts/python.exe -m uvicorn backend.logic:app --reload --host 127.0.0.1 --port 8002
```

### 3. Frontend (порт 5173) — третий терминал

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev -- --port 5173
```

### 4. Переменные окружения (задайте перед запуском uvicorn)

```powershell
$env:ML1_URL = 'http://localhost:8001/ocr'
$env:ML2_URL = 'http://localhost:8003/extract'
$env:BACKEND2_URL = 'http://localhost:8002/answer'
$env:CORS_ORIGINS = 'http://localhost:5173,http://127.0.0.1:5173'
$env:PADDLEOCR_VL_URL = 'http://127.0.0.1:8080/v1/chat/completions'
```

Файл `.env` бэкенд автоматически не загружает ( см. `docs/api.md`).

### 5. Сервисы ml1 и ml2 (нужны для обработки файлов)

```powershell
# ml1 (порт 8001)
pip install -r ml1/requirements.txt
python -m ml1.main

# ml2 (порт 8003)
python -m ml2.main
```

### 6. OCR-модель в режиме без Docker

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_llama.ps1
powershell -ExecutionPolicy Bypass -File scripts/run_llama.ps1
```

`run_llama.ps1` поднимает `llama-server.exe` на `127.0.0.1:8080` с моделями из `./models/`.

Откройте <http://localhost:5173>. Swagger API: <http://localhost:8000/docs>. Подробнее про интеграцию — в [docs/api.md](docs/api.md).

## Адреса сервисов после запуска

| Сервис | Порт | Назначение |
|--------|------|------------|
| Frontend | 5173 | веб-интерфейс |
| Backend API | 8000 | шлюз, авторизация, `/chat`, `/analyze`, Swagger |
| Backend 2 / правила | 8002 | детерминированная проверка документов, Swagger |
| ml1 / OCR | 8001 | PaddleOCR-VL через llama-server |
| ml2 / извлечение полей | 8003 | regex + опциональная LLM-правка полей |
| llama-server | 8080 | OCR-модель PaddleOCR-VL-1.6 на CPU |
| PostgreSQL | 5433 (→ 5432 внутри контейнера) | база личного кабинета и админки |

## Аккаунты и безопасность

Публичной регистрации и восстановления пароля по почте нет. Bootstrap-администратор создаётся при первом запуске с `BOOTSTRAP_ADMIN_EMAIL` и `BOOTSTRAP_ADMIN_PASSWORD`; дальше пользователей создаёт администратор. Минимальная длина пароля — 8 символов.

Вход доступен через `POST /api/auth/login`. После 10 попыток с одного IP за 15 минут следующая попытка получает `429`; неизвестный email и неверный пароль дают одинаковый ответ. При смене пароля администратором активные токены пользователя отзываются. Администратор может установить или сменить пароль через управление пользователями в Swagger (`/docs`). Изменения схемы БД применяются при старте; `/health` отвечает `503`, если настроенная БД недоступна или миграция не прошла. Подробности API и настройки — в [docs/api.md](docs/api.md).

## Как пользоваться

1. Откройте `http://localhost:5173` → `Загрузить документ`.
2. Выберите тип (или автоопределение), приложите JPG/PNG/PDF до 10 МБ, впишите вопрос, нажмите кнопку.
3. На странице результата: таблица полей, ответ секретаря, источники (`п. 3.x` или поле документа), подсветка найденного на фото, форма уточняющего вопроса в том же диалоге.

Три вида ответа: документ в порядке (`complete`), чего-то не хватает (`incomplete` + `missing_fields`), ответа нет (честно + `Обратитесь в деканат`). Проверка — это комплектность, решение всегда за сотрудником деканата.

## Пакетная проверка results.json

```powershell
python -m tools.make_results --input ./closed --output results.json --api-url http://localhost:8000
```

`closed/questions.json`: `[{id, file, question, document_type}]` (`document_type` опционален). Выход: `[{id, document:{type, fields}, answer, sources, verification, conversation_id}]`, ошибки — `{id, error}`. Пример на демо-документах: `demo_docs/questions.json` → `demo_results.json` (демо-PNG генерируются скриптом `python -m tools.make_demo_docs --output demo_docs`).

## Тесты

Из корня репозитория:

```powershell
.venv/Scripts/python.exe -m unittest discover -s backend/tests -q
.venv/Scripts/python.exe -m unittest discover -s ml1/tests -q
.venv/Scripts/python.exe -m unittest discover -s ml2/tests -q
cd frontend; npm test; npm run lint; npm run build
```

Проверка здоровья сервисов (после `docker compose up`):

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8002/health
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8003/health
Invoke-RestMethod http://localhost:8080/health
```

## Полезные команды

```powershell
docker compose up --build -d    # собрать и запустить все сервисы
docker compose up -d db          # только база данных (для локального запуска)
docker compose logs -f <сервис>  # логи: ml1, ml2, backend, rules, llama, db
docker compose down              # остановить и удалить контейнеры
docker compose restart rules     # перезапуск сервиса правил после изменения rules.json
```

Частые причины проблем: `llama` ещё грузит модели (в логе нет строки `listening`), старый бандл в браузере (лечится `Ctrl+F5`), нет `models/*.gguf`.

## Стек и инструменты

- Frontend: React 19 + TypeScript + Vite + TailwindCSS 4, Zustand, react-dropzone.
- Backend: Python 3.14 + FastAPI + Pydantic + httpx; PostgreSQL 15 для личного кабинета/админки (API работает и без БД).
- OCR: PaddleOCR-VL-1.6 (VLM 0.9B) через `llama.cpp llama-server` на CPU, OpenCV-препроцессинг, PyMuPDF для PDF.
- Извлечение полей: regex + словарь опечаток OCR + опциональная локальная LLM.
- Подпись и печать: YOLO11s Mels22 (`models/signature.onnx`), RF-DETR (`models/best.pth` + `models/config.json`, через `RFDETR_MODEL_PATH` / `RFDETR_CONFIG_PATH`), или классика синего кольца без весов (`YOLO_STAMP_HEURISTIC`). Координаты боксов передаются на фронт и подсвечиваются на фото.
- Правила: детерминированный движок `backend/rules.py` по JSON-базе `backend/data/rules.json` (п. 3.1–3.3 из презентации кейса; шаблон — `backend/data/university-rules.template.json`, подключение через `RULES_PATH` без изменения кода).

## Документация

- [docs/api.md](docs/api.md) — контракт интеграции и запуск без Docker.
- [docs/demo_script.md](docs/demo_script.md) — сценарий 3-минутного демо.
- [docs/testing.md](docs/testing.md) — как протестировать проект.
- [models/README.md](models/README.md) — модели OCR и детектор подписей.
