import { MAX_FILE_SIZE, MAX_QUESTION_LENGTH } from "./types.ts"
import type { AnalysisResult, DocumentType } from "./types.ts"
import { isDocumentImage } from "./highlights.ts"

export * from "./types.ts"

const API_URL = (import.meta.env?.VITE_API_URL ?? "http://localhost:8000").replace(/\/+$/, "")
// /analyze последовательно вызывает три сервиса с таймаутом по 60 секунд.
const REQUEST_TIMEOUT_MS = 200_000

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status = 0) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function errorDetail(body: unknown): string | undefined {
  if (!isRecord(body)) return
  if (typeof body.detail === "string") return body.detail
  if (Array.isArray(body.detail)) {
    return body.detail.map((item: unknown) => {
      if (!isRecord(item) || typeof item.msg !== "string") return "Некорректные данные запроса"
      return `${Array.isArray(item.loc) ? item.loc.slice(1).join(".") + ": " : ""}${item.msg}`
    }).join("; ")
  }
}

function parseResult(body: unknown): AnalysisResult {
  if (!isRecord(body) || typeof body.conversation_id !== "string" ||
      typeof body.answer !== "string" || !Array.isArray(body.sources) ||
      !body.sources.every((source: unknown) => isRecord(source) &&
        typeof source.type === "string" && typeof source.reference === "string" &&
        (source.url == null || typeof source.url === "string"))) {
    throw new ApiError("Сервер вернул некорректный ответ", 502)
  }
  const doc = body.document
  if (doc !== null && (!isRecord(doc) || !isRecord(doc.fields) ||
      (doc.type !== null && typeof doc.type !== "string") ||
      typeof doc.ocr_text !== "string" || !Array.isArray(doc.coordinates) ||
      (doc.image != null && !isDocumentImage(doc.image)))) {
    throw new ApiError("Сервер вернул некорректные данные документа", 502)
  }
  if (isRecord(doc) && doc.visual_features != null) {
    const features = doc.visual_features
    if (!isRecord(features) || !["ready", "disabled", "error"].includes(features.status as string) ||
        ![true, false, null].includes(features.signature as boolean | null) ||
        ![true, false, null].includes(features.stamp as boolean | null)) {
      throw new ApiError("Сервер вернул некорректный результат проверки подписи и печати", 502)
    }
  }
  const verification = body.verification ?? null
  if (verification !== null && (!isRecord(verification) || typeof verification.status !== "string" ||
      !Array.isArray(verification.missing_fields) || !verification.missing_fields.every((v: unknown) => typeof v === "string") ||
      !Array.isArray(verification.issues) || !verification.issues.every((v: unknown) => typeof v === "string"))) {
    throw new ApiError("Сервер вернул некорректный результат проверки", 502)
  }
  return { ...body, verification } as unknown as AnalysisResult
}

async function request(path: string, init: RequestInit): Promise<AnalysisResult> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_URL}${path}`, { ...init, signal: controller.signal })
    const body: unknown = await response.json().catch((error: unknown) => {
      if (controller.signal.aborted) throw error
      return null
    })
    if (!response.ok) {
      throw new ApiError(errorDetail(body) || `Ошибка сервера (${response.status})`, response.status)
    }
    return parseResult(body)
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted) throw new ApiError("Время ожидания ответа истекло. Попробуйте ещё раз.")
    throw new ApiError("Не удалось подключиться к серверу. Проверьте соединение и доступность backend.")
  } finally {
    clearTimeout(timer)
  }
}

function validateQuestion(question: string): string {
  const value = question.trim()
  if (!value) throw new ApiError("Введите вопрос")
  if (value.length > MAX_QUESTION_LENGTH) throw new ApiError(`Максимальная длина вопроса — ${MAX_QUESTION_LENGTH} символов`)
  return value
}

export function validateFile(file: File): void {
  if (!/\.(jpe?g|png|pdf)$/i.test(file.name)) throw new ApiError("Разрешены JPG, PNG и PDF")
  if (!file.size) throw new ApiError("Файл пустой")
  if (file.size > MAX_FILE_SIZE) throw new ApiError("Максимальный размер файла — 10 МБ")
}

export async function sendMessage(message: string, conversationId?: string): Promise<AnalysisResult> {
  return request("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: validateQuestion(message), conversation_id: conversationId }),
  })
}

export async function analyzeDocument({ file, question, docType, conversationId }: {
  file: File
  question: string
  docType?: DocumentType | ""
  conversationId?: string
}): Promise<AnalysisResult> {
  validateFile(file)
  const body = new FormData()
  body.append("file", file, file.name)
  body.append("question", validateQuestion(question))
  if (docType) body.append("document_type", docType)
  if (conversationId) body.append("conversation_id", conversationId)
  return request("/analyze", { method: "POST", body })
}
