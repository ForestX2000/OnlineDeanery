import assert from "node:assert/strict"
import { after, beforeEach, test } from "node:test"

const storage = new Map()
globalThis.localStorage = {
  getItem: (key) => storage.get(key) ?? null,
  setItem: (key, value) => storage.set(key, value),
  removeItem: (key) => storage.delete(key),
}
const { useAppStore } = await import("../src/store/useAppStore.ts")
const originalCreate = URL.createObjectURL
const originalRevoke = URL.revokeObjectURL
const revoked = []
let created = 0
URL.createObjectURL = () => `blob:preview-${++created}`
URL.revokeObjectURL = (url) => revoked.push(url)
beforeEach(() => {
  useAppStore.getState().reset()
  revoked.length = 0
})
after(() => {
  useAppStore.getState().reset()
  URL.createObjectURL = originalCreate
  URL.revokeObjectURL = originalRevoke
  delete globalThis.localStorage
})

const result = {
  conversation_id: "one", answer: "Ответ", sources: [], verification: null,
  document: { type: null, fields: {}, ocr_text: "текст", coordinates: [] },
}
const file = () => new File(["photo"], "document.png", { type: "image/png" })

test("preview survives conversation followups and is never persisted", () => {
  useAppStore.getState().setResult(result, file())
  const preview = useAppStore.getState().preview
  useAppStore.getState().setResult({ ...result, answer: "Уточнение" })
  assert.equal(useAppStore.getState().preview, preview)
  assert.deepEqual(revoked, [])
  const saved = JSON.parse(storage.get("online-deanery-storage"))
  assert.equal(saved.state.preview, undefined)
  assert.equal(saved.state.file, undefined)
  assert.equal(JSON.stringify(saved).includes("blob:"), false)
})

test("replacing the document revokes the old blob and binds the new preview to its conversation", () => {
  useAppStore.getState().setResult(result, file())
  const first = useAppStore.getState().preview.url
  useAppStore.getState().setResult({ ...result, conversation_id: "two" }, file())
  assert.deepEqual(revoked, [first])
  assert.equal(useAppStore.getState().preview.conversationId, "two")
  assert.notEqual(useAppStore.getState().preview.url, first)
})

test("a different conversation or absent document cannot inherit the old photo", () => {
  for (const next of [{ ...result, conversation_id: "two" }, { ...result, document: null }]) {
    useAppStore.getState().setResult(result, file())
    const previous = useAppStore.getState().preview.url
    useAppStore.getState().setResult(next)
    assert.equal(useAppStore.getState().preview, null)
    assert.ok(revoked.includes(previous))
  }
})

test("PDF and text-only uploads clear the previous photo", () => {
  for (const source of [new File(["%PDF"], "document.pdf", { type: "application/pdf" }), null]) {
    useAppStore.getState().setResult(result, file())
    const previous = useAppStore.getState().preview.url
    useAppStore.getState().setResult(result, source)
    assert.equal(useAppStore.getState().preview, null)
    assert.ok(revoked.includes(previous))
  }
})

test("reset and logout each release the preview", () => {
  for (const action of ["reset", "logout"]) {
    useAppStore.getState().setResult(result, file())
    const previous = useAppStore.getState().preview.url
    useAppStore.getState()[action]()
    assert.equal(useAppStore.getState().preview, null)
    assert.equal(useAppStore.getState().result, null)
    assert.ok(revoked.includes(previous))
  }
})
