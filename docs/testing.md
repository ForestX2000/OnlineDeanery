# Как протестировать проект

Все команды — PowerShell из корня репозитория.

## 1. Юниты и сборка

```powershell
.venv/Scripts/python.exe -m unittest discover -s backend/tests -q
.venv/Scripts/python.exe -m unittest discover -s ml1/tests -q
.venv/Scripts/python.exe -m unittest discover -s ml2/tests -q
cd frontend; npm test; npm run lint; npm run build; cd ..
```

Ожидается: 52 + 38 + 7 + 24 зеленых теста, `tsc` и `vite build` без ошибок.

## 2. Здоровье сервисов

```powershell
docker compose ps
Invoke-RestMethod http://localhost:8000/health
Invoke-RestMethod http://localhost:8002/health
Invoke-RestMethod http://localhost:8001/health
Invoke-RestMethod http://localhost:8003/health
Invoke-RestMethod http://localhost:8080/health
```

## 3. Ручные сценарии (http://localhost:5173)

1. Без файла: `Сколько стоит обучение?` — ответ `Ответа нет`, `verification: null`.
2. `baton.png` + `Хватит ли её для перевода на 2 курс?` — `complete`,
   источник `п. 3.1`, подсветка подписи и печати на фото.
3. `demo_docs/academic_leave.png` + `Чего не хватает?` — проверка дат.
4. Там же уточняющий вопрос `Что там написано?` — перечень полей
   без повторной загрузки файла.
5. PDF-версия фото — проходит через растеризацию первой страницы.

Перед сценариями 2–5: `Ctrl+F5` в браузере, чтобы подхватить свежий бандл.

## 4. Пакетная проверка (образец results.json)

```powershell
python -m tools.make_demo_docs --output demo_docs
python -m tools.make_results --input ./demo_docs --output results.json --api-url http://localhost:8000
```

У всех трех документов в `results.json` должно быть
`verification.status: complete`.

## 5. Авторизация и БД

```powershell
curl.exe -s -X POST http://localhost:8000/api/auth/login -H 'Content-Type: application/json' -d '{\"email\":\"nobody@x.ru\",\"password\":\"x\"}'
```

Неизвестный email — `401` с русским текстом: связка API с PostgreSQL жива.

## 6. Если что-то красное

```powershell
docker compose logs backend --tail=30
docker compose logs ml1 --tail=30
docker compose logs ml2 --tail=30
docker compose logs llama --tail=10
```

Частые причины: `llama` еще грузит модели (`listening` нет в логе),
старый бандл в браузере (лечится `Ctrl+F5`), нет `models/*.gguf`.
