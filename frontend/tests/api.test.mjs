import assert from "node:assert/strict"
import { afterEach, test } from "node:test"
import { analyzeDocument, ApiError, MAX_FILE_SIZE, sendMessage, validateFile } from "../api/index.ts"

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
