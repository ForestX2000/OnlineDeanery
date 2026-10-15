# Онлайн-деканат

Цифровой секретарь: читает фото студенческого документа (OCR), заполняет
карточку полей и отвечает на вопрос со ссылкой на пункты правил.
Пайплайн: распознать текст → разложить данные по полям → ответить со ссылкой.

## Быстрый запуск через Docker

Нужен установленный и запущенный Docker Desktop с поддержкой `docker compose`.
Node.js и Python на компьютере устанавливать не нужно.

```powershell
git clone https://github.com/ForestX2000/OnlineDeanery.git
cd OnlineDeanery
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

Перед запуском откройте `.env` и задайте обязательный `POSTGRES_PASSWORD` — случайный
URL-safe секрет не короче 32 символов. Не используйте пароль из примера и не коммитьте
`.env`. Чтобы включить вход, историю и администрирование, задайте также
`BOOTSTRAP_ADMIN_EMAIL` и `BOOTSTRAP_ADMIN_PASSWORD` (от 8 символов) до первого запуска.
Если bootstrap-учётные данные не заданы, сервис запустится без начального администратора;
загрузка и обработка документов останутся доступны.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_llama.ps1
docker compose up --build -d
```

`install_llama.ps1` скачивает `llama-server` и оба `.gguf` в `./models/`
(в git не входят, см. `models/README.md`). Одна команда поднимает всё,
включая OCR: отдельный `llama-server.exe` больше не нужен.

После запуска откройте:

- Frontend: <http://localhost:5173>
- API и Swagger: <http://localhost:8000/docs>, здоровье: <http://localhost:8000/health>
- Сервис правил и Swagger: <http://localhost:8002/docs>, здоровье: <http://localhost:8002/health>

Фон: `docker compose up --build -d`. Логи: `docker compose logs -f [ml1|ml2|backend|rules|llama]`.
Остановка: `docker compose down`.

Вопрос **без файла** работает сразу (frontend + API + правила).
С файлом нужны `ml1` (OCR через compose-сервис `llama`) и `ml2` (поля).
Без `models/*.gguf` сервис `llama` перезапускается, `ml1` вернет `503`.
PDF растеризуется первой страницей в `ml1` (PyMuPDF).

Если адреса отличаются, создайте `.env` на основе `.env.example` и укажите
`PADDLEOCR_VL_URL`, `ML1_URL`, `ML2_URL`, затем перезапустите:

```powershell
Copy-Item .env.example .env
docker compose up --build -d
```

Контракт интеграции и запуск без Docker — в [docs/api.md](docs/api.md).
Сценарий 3-минутного демо — в [docs/demo_script.md](docs/demo_script.md).

## Аккаунты и безопасность

Публичной регистрации и восстановления пароля по почте нет. Bootstrap-администратор
создаётся при первом запуске с `BOOTSTRAP_ADMIN_EMAIL` и `BOOTSTRAP_ADMIN_PASSWORD`;
дальше пользователей создаёт администратор. Минимальная длина пароля — 8 символов.

Вход доступен через `POST /api/auth/login`. После 10 попыток с одного IP за 15 минут
следующая попытка получает `429`; неизвестный email и неверный пароль дают одинаковый
ответ. При смене пароля администратором активные токены пользователя отзываются.
Администратор может установить или сменить пароль через управление пользователями в Swagger (`/docs`).
Изменения схемы БД применяются при старте; `/health` отвечает `503`, если настроенная БД
недоступна или миграция не прошла. Подробности API и настройки — в [docs/api.md](docs/api.md).

Создание аккаунта администратора в .env:
BOOTSTRAP_ADMIN_EMAIL=admin@university.ru
BOOTSTRAP_ADMIN_PASSWORD=admin123
BOOTSTRAP_ADMIN_NAME=Алексей Админов

## Как пользоваться

1. Откройте `http://localhost:5173` → `Загрузить документ`.
2. Выберите тип (или автоопределение), приложите JPG/PNG/PDF до 10 МБ,
   впишите вопрос, нажмите кнопку.
3. На странице результата: таблица полей, ответ секретаря, источники
   (`п. 3.x` или поле документа), подсветка найденного на фото,
   форма уточняющего вопроса в том же диалоге.

Три вида ответа: документ в порядке (`complete`), чего-то не хватает
(`incomplete` + `missing_fields`), ответа нет (честно + `Обратитесь в деканат`).
Проверка — это комплектность, решение всегда за сотрудником деканата.

## Стек и инструменты

- Frontend: React 19 + TypeScript + Vite + TailwindCSS 4, Zustand, react-dropzone.
- Backend: Python 3.14 + FastAPI + Pydantic + httpx; PostgreSQL 15 для
  личного кабинета/админки (API работает и без БД).
- OCR: PaddleOCR-VL-1.6 (VLM 0.9B) через `llama.cpp llama-server` на CPU,
  OpenCV-препроцессинг, PyMuPDF для PDF.
- Извлечение полей: regex + словарь опечаток OCR + опциональная локальная LLM.
- Подпись: YOLO11s Mels22 (`models/signature.onnx`, экспорт в `models/README.md`).
  Печать: классика синего кольца без весов (`YOLO_STAMP_HEURISTIC`),
  своя YOLO-печать подключается через `YOLO_MODEL_PATH`.
- Правила: детерминированный движок `backend/rules.py` по JSON-базе
  `backend/data/rules.json` (п. 3.1–3.3 из презентации кейса;
  настоящее Положение заказчик не предоставил, шаблон —
  `backend/data/university-rules.template.json`, подключение через `RULES_PATH`
  без изменения кода). Внешние LLM API не используются.

## results.json для закрытой проверки

```powershell
python -m tools.make_results --input ./closed --output results.json --api-url http://localhost:8000
```

`closed/questions.json`: `[{id, file, question, document_type}]`
(`document_type` опционален). Выход: `[{id, document:{type, fields},
answer, sources, verification, conversation_id}]`, ошибки — `{id, error}`.
Пример на демо-документах: `demo_docs/questions.json` → `demo_results.json`
(демо-PNG генерируются скриптом `python -m tools.make_demo_docs`).

## Проверки

```powershell
.venv/Scripts/python.exe -m unittest discover -s backend/tests -q
.venv/Scripts/python.exe -m unittest discover -s ml1/tests -q
.venv/Scripts/python.exe -m unittest discover -s ml2/tests -q
cd frontend; npm test; npm run lint; npm run build
```
