# Как протестировать проект

Все команды — PowerShell из корня репозитория.

## 1. Юниты и сборка

```powershell
.venv/Scripts/python.exe -m unittest discover -s backend/tests -q
.venv/Scripts/python.exe -m unittest discover -s ml1/tests -q
.venv/Scripts/python.exe -m unittest discover -s ml2/tests -q
cd frontend; npm test; npm run lint; npm run build; cd ..
```

Ожидается, что все наборы тестов, `tsc` и `vite build` завершатся без ошибок.

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
2. `demo_docs/study_certificate.png` + `Хватит ли её для перевода на 2 курс?` — `complete`,
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

Неизвестный email — такой же `401` «Неверный email или пароль», как и неверный пароль.
11-я попытка за 15 минут с одного IP получает `429` с `Retry-After`.

## 6. Если что-то красное

```powershell
docker compose logs backend --tail=30
docker compose logs ml1 --tail=30
docker compose logs ml2 --tail=30
docker compose logs llama --tail=10
```

## Добавление нового типа документа через конфигурацию

Добавьте запись в `document_types` файла `backend/data/rules.json`. Для каждого поля укажите `name`, `label`, `aliases`, `reference` и `kind` (`text`, `date` или `boolean`). Значения распознаются по подписи или синониму на той же строке либо на следующей. Если тип должен ссылаться на конкретное правило, добавьте его идентификатор в `document_types` соответствующего пункта в `clauses`.

Пример записи типа:

```json
"custom_invoice": {
  "label": "Счёт",
  "aliases": ["Счёт на оплату"],
  "required_fields": [
    {
      "name": "invoice_number",
      "label": "Номер счёта",
      "aliases": ["Регистрационный номер"],
      "reference": "4.1",
      "kind": "text",
      "must_be_true": false
    }
  ]
}
```

Каталог типов и названия полей загружаются из этого файла. Новый тип можно выбрать вручную;
для его автоматического распознавания дополнительно добавьте признаки в `ml2/classify.py`.
После изменения конфигурации перезапустите `rules`:

```powershell
docker compose restart rules
```

Частые причины: `llama` еще грузит модели (`listening` нет в логе),
старый бандл в браузере (лечится `Ctrl+F5`), нет `models/*.gguf`.
