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

Сервисы OCR и извлечения полей пока не входят в репозиторий. Поэтому загрузка
файла заработает, если отдельно запустить совместимые сервисы на хосте:

- OCR: `http://localhost:8001/ocr`
- Extract: `http://localhost:8003/extract`

Compose обращается к сервисам на компьютере через `host.docker.internal`.
Если адреса отличаются, создайте `.env` на основе `.env.example` и укажите
`ML1_URL` и `ML2_URL`, затем перезапустите контейнеры:

```powershell
Copy-Item .env.example .env
docker compose up --build
```

Контракт интеграции и запуск без Docker описаны в [docs/api.md](docs/api.md).
