import assert from "node:assert/strict"
import { afterEach, test } from "node:test"
import { analyzeDocument, ApiError, forgotPasswordRequest, getDocumentTypes, loginRequest, MAX_FILE_SIZE, sendMessage, validateFile } from "../api/index.ts"

const originalFetch = globalThis.fetch
afterEach(() => { globalThis.fetch = originalFetch })
const answer = {
  conversation_id: "test-conversation", answer: "Ответ по Положению", sources: [],
  document: null, verification: null,
}

test("chat sends trimmed JSON and the conversation ID", async () => {
  globalThis.fetch = async (url, init) => {
    assert.equal(url, "http://localhost:8000/chat")
    assert.equal(init.method, "POST")
    assert.equal(init.headers["Content-Type"], "application/json")
    assert.deepEqual(JSON.parse(init.body), { message: "Вопрос?", conversation_id: "existing" })
    assert.ok(init.signal instanceof AbortSignal)
    return Response.json(answer)
  }
  assert.deepEqual(await sendMessage("  Вопрос?  ", "existing"), answer)
})

test("analysis sends the original file with multipart fields and lets fetch set the boundary", async () => {
  const file = new File(["%PDF-test"], "document.pdf", { type: "application/pdf" })
  globalThis.fetch = async (url, init) => {
    assert.equal(url, "http://localhost:8000/analyze")
    assert.equal(init.headers, undefined)
    assert.ok(init.body instanceof FormData)
    assert.equal(await init.body.get("file").text(), await file.text())
    assert.equal(init.body.get("file").name, file.name)
    assert.equal(init.body.get("question"), "Подходит?")
    assert.equal(init.body.get("document_type"), "study_certificate")
    assert.equal(init.body.get("conversation_id"), "existing")
    return Response.json(answer)
  }
  await analyzeDocument({ file, question: " Подходит? ", docType: "study_certificate", conversationId: "existing" })
})

test("automatic classification omits the document type and new conversation ID", async () => {
  globalThis.fetch = async (_, init) => {
    assert.equal(init.body.has("document_type"), false)
    assert.equal(init.body.has("conversation_id"), false)
    return Response.json(answer)
  }
  await analyzeDocument({ file: new File(["image"], "photo.PNG"), question: "Вопрос?" })
})

test("document types and their field labels come from the configuration", async () => {
  const catalog = { items: [{ id: "custom_invoice", label: "Счёт", required_fields: [
    { name: "invoice_number", label: "Номер счёта" },
  ] }] }
  globalThis.fetch = async (url, init) => {
    assert.equal(url, "http://localhost:8000/document-types")
    assert.ok(init.signal instanceof AbortSignal)
    return Response.json(catalog)
  }
  assert.deepEqual(await getDocumentTypes(), catalog.items)

  globalThis.fetch = async () => Response.json({ items: [{ id: "broken", label: "Broken", required_fields: "not-an-array" }] })
  await assert.rejects(getDocumentTypes(), (error) => error instanceof ApiError && error.status === 502)
})

test("invalid input is rejected before making a request", async () => {
  globalThis.fetch = () => { assert.fail("fetch must not be called") }
  await assert.rejects(sendMessage("  "), /Введите вопрос/)
  await assert.rejects(sendMessage("x".repeat(5001)), /5000/)
  assert.throws(() => validateFile(new File([], "empty.pdf")), /пустой/)
  assert.throws(() => validateFile(new File(["test"], "test.exe")), /JPG/)
  assert.throws(() => validateFile(new File([new Uint8Array(MAX_FILE_SIZE + 1)], "large.pdf")), /10 МБ/)
})

test("backend error details and HTTP status are preserved", async () => {
  globalThis.fetch = async () => Response.json({ detail: "Диалог не найден" }, { status: 404 })
  await assert.rejects(sendMessage("Вопрос?"), (error) => error instanceof ApiError && error.status === 404 && error.message === "Диалог не найден")
})

test("FastAPI validation errors are readable", async () => {
  globalThis.fetch = async () => Response.json({ detail: [{ loc: ["body", "question"], msg: "Field required" }] }, { status: 422 })
  await assert.rejects(sendMessage("Вопрос?"), /question: Field required/)
})

test("non-JSON HTTP errors keep their status", async () => {
  globalThis.fetch = async () => new Response("<html>Unavailable</html>", { status: 503 })
  await assert.rejects(sendMessage("Вопрос?"), (error) => error.status === 503)
})

test("malformed success responses cannot reach the components", async () => {
  for (const body of [null, {}, { ...answer, sources: null }, { ...answer, document: {} }, { ...answer, verification: { status: "ok" } }]) {
    globalThis.fetch = async () => Response.json(body)
    await assert.rejects(sendMessage("Вопрос?"), (error) => error.status === 502)
  }
})

test("network errors are shown as a connection problem", async () => {
  globalThis.fetch = async () => { throw new TypeError("Failed to fetch") }
  await assert.rejects(sendMessage("Вопрос?"), /Не удалось подключиться/)
})

test("login posts credentials and returns the user", async () => {
  const payload = { success: true, token: "t", user: { email: "s@u.ru", firstName: "Иван", lastName: "С", role: "student" } }
  globalThis.fetch = async (url, init) => {
    assert.equal(url, "http://localhost:8000/api/auth/login")
    assert.deepEqual(JSON.parse(init.body), { email: "s@u.ru", password: "pw" })
    return Response.json(payload)
  }
  assert.deepEqual(await loginRequest("  s@u.ru ", "pw"), payload)
  globalThis.fetch = async () => Response.json({ detail: "Неверный пароль" }, { status: 401 })
  await assert.rejects(loginRequest("s@u.ru", "pw"), (error) => error.status === 401 && /пароль/.test(error.message))
  await assert.rejects(loginRequest("  ", "pw"), /email и пароль/)
})

test("forgot password returns the server message", async () => {
  globalThis.fetch = async (url, init) => {
    assert.equal(url, "http://localhost:8000/api/auth/forgot-password")
    assert.deepEqual(JSON.parse(init.body), { email: "s@u.ru" })
    return Response.json({ success: true, message: "Пароль отправлен" })
  }
  assert.equal(await forgotPasswordRequest("s@u.ru"), "Пароль отправлен")
  globalThis.fetch = async () => Response.json({ detail: "Не зарегистрирован" }, { status: 404 })
  await assert.rejects(forgotPasswordRequest("s@u.ru"), (error) => error.status === 404)
})

test("image geometry and visual detection status survive the API boundary", async () => {
  const document = {
    type: "study_certificate", fields: { stamp: null, signature: null }, ocr_text: "Текст",
    image: { width: 1600, height: 900, rotation: 90 },
    visual_features: { status: "disabled", signature: null, stamp: null },
    coordinates: [{ field: null, text: "Текст", bbox: [0, 0, 200, 100], confidence: null, source: "spotting", page: 1 }],
  }
  globalThis.fetch = async () => Response.json({ ...answer, document })
  assert.deepEqual((await sendMessage("Вопрос?")).document, document)
})

test("legacy documents without image metadata still work", async () => {
  const document = { type: null, fields: {}, ocr_text: "Текст", coordinates: [{ x: 10, y: 20 }] }
  globalThis.fetch = async () => Response.json({ ...answer, document })
  assert.deepEqual((await sendMessage("Вопрос?")).document, document)
})

test("invalid optional image metadata or detection status is rejected", async () => {
  const document = { type: null, fields: {}, ocr_text: "Текст", coordinates: [] }
  for (const extra of [{ image: {} }, { image: { width: 0, height: 900, rotation: 0 } },
    { image: { width: 1600, height: 900, rotation: "90" } },
    { visual_features: { status: "disabled", signature: "false", stamp: null } }]) {
    globalThis.fetch = async () => Response.json({ ...answer, document: { ...document, ...extra } })
    await assert.rejects(sendMessage("Вопрос?"), (error) => error.status === 502)
  }
})
