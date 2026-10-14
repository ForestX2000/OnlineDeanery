import { MAX_FILE_SIZE, MAX_QUESTION_LENGTH } from "./types.ts"
import type { AnalysisResult, DocumentData, DocumentType, DocumentTypeOption, LoginResult, RequestHistoryItem } from "./types.ts"
import { isDocumentImage } from "./highlights.ts"

export * from "./types.ts"

const API_URL = (import.meta.env?.VITE_API_URL ?? "http://localhost:8000").replace(/\/+$/, "")
// Два прохода OCR могут занять до 270 секунд плюс последующий анализ.
const REQUEST_TIMEOUT_MS = 390_000

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

function bearerHeaders(token?: string): Record<string, string> {
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export async function sendMessage(message: string, conversationId?: string, token?: string): Promise<AnalysisResult> {
  return request("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json", ...bearerHeaders(token) },
    body: JSON.stringify({ message: validateQuestion(message), conversation_id: conversationId }),
  })
}

type AnalysisProgress = "ocr" | "extract" | "answer"

async function analyzeDocumentStream({
  file, question, docType, conversationId, token, onFields, onProgress,
}: {
  file: File
  question: string
  docType?: DocumentType | ""
  conversationId?: string
  token?: string
  onFields?: (document: DocumentData) => void
  onProgress?: (stage: AnalysisProgress) => void
}): Promise<AnalysisResult> {
  const body = new FormData()
  body.append("file", file, file.name)
  body.append("question", validateQuestion(question))
  if (docType) body.append("document_type", docType)
  if (conversationId) body.append("conversation_id", conversationId)

  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS)
  try {
    const response = await fetch(`${API_URL}/analyze/stream`, {
      method: "POST",
      headers: bearerHeaders(token),
      body,
      signal: controller.signal,
    })
    if (!response.ok) {
      const bodyJson: unknown = await response.json().catch(() => null)
      throw new ApiError(errorDetail(bodyJson) || `Ошибка сервера (${response.status})`, response.status)
    }
    if (!response.body) throw new ApiError("Сервер не открыл поток обработки", 502)

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""
    let finalResult: AnalysisResult | null = null

    const handleLine = (line: string) => {
      if (!line.trim()) return
      let event: unknown
      try { event = JSON.parse(line) } catch { throw new ApiError("Сервер передал некорректное событие обработки", 502) }
      if (!isRecord(event) || typeof event.type !== "string") {
        throw new ApiError("Сервер передал некорректное событие обработки", 502)
      }
      if (event.type === "progress" && ["ocr", "extract", "answer"].includes(event.stage as string)) {
        onProgress?.(event.stage as AnalysisProgress)
      } else if (event.type === "fields") {
        const partial = parseResult({
          conversation_id: "processing",
          answer: "Обработка продолжается",
          sources: [],
          document: event.document,
        })
        if (partial.document) onFields?.(partial.document)
      } else if (event.type === "result") {
        finalResult = parseResult(event.result)
      } else if (event.type === "error") {
        throw new ApiError(typeof event.detail === "string" ? event.detail : "Не удалось обработать документ",
          typeof event.status === "number" ? event.status : 500)
      }
    }

    while (true) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      const lines = buffer.split("\n")
      buffer = lines.pop() ?? ""
      for (const line of lines) handleLine(line)
      if (done) break
    }
    if (buffer.trim()) handleLine(buffer)
    if (!finalResult) throw new ApiError("Обработка завершилась без итогового ответа", 502)
    return finalResult
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted) throw new ApiError("Время ожидания ответа истекло. Попробуйте ещё раз.")
    throw new ApiError("Поток обработки прерван. Проверьте соединение с сервером.")
  } finally {
    clearTimeout(timer)
  }
}

export async function analyzeDocument({ file, question, docType, conversationId, token, onFields, onProgress }: {
  file: File
  question: string
  docType?: DocumentType | ""
  conversationId?: string
  token?: string
  onFields?: (document: DocumentData) => void
  onProgress?: (stage: AnalysisProgress) => void
}): Promise<AnalysisResult> {
  validateFile(file)
  if (onFields || onProgress) {
    return analyzeDocumentStream({ file, question, docType, conversationId, token, onFields, onProgress })
  }
  const body = new FormData()
  body.append("file", file, file.name)
  body.append("question", validateQuestion(question))
  if (docType) body.append("document_type", docType)
  if (conversationId) body.append("conversation_id", conversationId)
  return request("/analyze", { method: "POST", headers: token ? bearerHeaders(token) : undefined, body })
}

function parseAuth(body: unknown): LoginResult {
  if (!isRecord(body) || typeof body.success !== "boolean" || typeof body.token !== "string" ||
      !isRecord(body.user) || typeof body.user.email !== "string") {
    throw new ApiError("Сервер вернул некорректный ответ входа", 502)
  }
  const user = body.user
  return {
    success: body.success as boolean,
    token: body.token as string,
    user: {
      email: user.email as string,
      firstName: typeof user.firstName === "string" ? user.firstName : "",
      lastName: typeof user.lastName === "string" ? user.lastName : "",
      role: typeof user.role === "string" ? user.role : "student",
    },
  }
}

async function authRequest(path: string, payload: Record<string, string>): Promise<unknown> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 30_000)
  try {
    const response = await fetch(`${API_URL}${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    })
    const body: unknown = await response.json().catch(() => null)
    if (!response.ok) {
      throw new ApiError(errorDetail(body) || `Ошибка сервера (${response.status})`, response.status)
    }
    return body
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted) throw new ApiError("Время ожидания ответа истекло. Попробуйте ещё раз.")
    throw new ApiError("Не удалось подключиться к серверу. Проверьте соединение и доступность backend.")
  } finally {
    clearTimeout(timer)
  }
}

export async function loginRequest(email: string, password: string): Promise<LoginResult> {
  const trimmed = email.trim()
  if (!trimmed || !password) throw new ApiError("Введите email и пароль")
  return parseAuth(await authRequest("/api/auth/login", { email: trimmed, password }))
}

export async function logoutRequest(token: string): Promise<void> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 30_000)
  try {
    const response = await fetch(`${API_URL}/api/auth/logout`, {
      method: "POST",
      headers: bearerHeaders(token),
      signal: controller.signal,
    })
    if (!response.ok) {
      const body: unknown = await response.json().catch(() => null)
      throw new ApiError(errorDetail(body) || `Ошибка сервера (${response.status})`, response.status)
    }
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted) throw new ApiError("Время ожидания ответа истекло. Попробуйте ещё раз.")
    throw new ApiError("Не удалось подключиться к серверу. Проверьте соединение и доступность backend.")
  } finally {
    clearTimeout(timer)
  }
}

export async function getRequestHistory(token: string): Promise<RequestHistoryItem[]> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 30_000)
  try {
    const response = await fetch(`${API_URL}/api/requests`, { headers: bearerHeaders(token), signal: controller.signal })
    const body: unknown = await response.json().catch(() => null)
    if (!response.ok) {
      throw new ApiError(errorDetail(body) || `Ошибка сервера (${response.status})`, response.status)
    }
    if (!Array.isArray(body) || !body.every((item: unknown) => isRecord(item) &&
        Number.isInteger(item.request_id) && typeof item.question === "string" &&
        (item.answer === null || typeof item.answer === "string") && typeof item.status === "string" &&
        typeof item.created_at === "string" && typeof item.user_email === "string" &&
        typeof item.user_name === "string")) {
      throw new ApiError("Сервер вернул некорректную историю запросов", 502)
    }
    return body as RequestHistoryItem[]
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted) throw new ApiError("Время ожидания ответа истекло. Попробуйте ещё раз.")
    throw new ApiError("Не удалось подключиться к серверу. Проверьте соединение и доступность backend.")
  } finally {
    clearTimeout(timer)
  }
}

export async function getDocumentTypes(): Promise<DocumentTypeOption[]> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 15_000)
  try {
    const response = await fetch(`${API_URL}/document-types`, { signal: controller.signal })
    const body: unknown = await response.json().catch(() => null)
    if (!response.ok) throw new ApiError(errorDetail(body) || `Ошибка сервера (${response.status})`, response.status)
    if (!isRecord(body) || !Array.isArray(body.items) || !body.items.every((item: unknown) =>
      isRecord(item) && typeof item.id === "string" && typeof item.label === "string" &&
      (item.required_fields === undefined || (Array.isArray(item.required_fields) && item.required_fields.every((field: unknown) =>
        isRecord(field) && typeof field.name === "string" && typeof field.label === "string"))))) {
      throw new ApiError("Сервер вернул некорректный список типов документов", 502)
    }
    const items = body.items as Array<Record<string, unknown>>
    return items.map((item) => ({
      id: item.id as string,
      label: item.label as string,
      required_fields: Array.isArray(item.required_fields)
        ? (item.required_fields as Array<Record<string, unknown>>).map((field) => ({
          name: field.name as string,
          label: field.label as string,
        }))
        : undefined,
    }))
  } catch (error) {
    if (error instanceof ApiError) throw error
    if (controller.signal.aborted) throw new ApiError("Не удалось загрузить типы документов")
    throw new ApiError("Не удалось подключиться к серверу. Проверьте соединение и доступность backend.")
  } finally {
    clearTimeout(timer)
  }
}

export async function forgotPasswordRequest(email: string): Promise<string> {
  const trimmed = email.trim()
  if (!trimmed) throw new ApiError("Введите email")
  const body = await authRequest("/api/auth/forgot-password", { email: trimmed })
  if (!isRecord(body) || typeof body.message !== "string") {
    throw new ApiError("Сервер вернул некорректный ответ", 502)
  }
  return body.message
}
