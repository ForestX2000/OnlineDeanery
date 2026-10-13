export const MAX_FILE_SIZE = 10 * 1024 * 1024
export const MAX_QUESTION_LENGTH = 5000

export const DOCUMENT_LABELS = {
  study_certificate: "Справка об обучении",
  academic_leave: "Заявление на академический отпуск",
  internship_certificate: "Справка о практике",
} as const

export type DocumentType = keyof typeof DOCUMENT_LABELS
export type JsonValue = string | number | boolean | null | JsonValue[] | { [key: string]: JsonValue }

export interface Source {
  type: string
  reference: string
  url?: string | null
}

export interface DocumentImage {
  width: number
  height: number
  rotation: 0 | 90 | 180 | 270
}

export interface DocumentCoordinate {
  field: string | null
  text: string
  bbox: [number, number, number, number]
  confidence: number | null
  source: "yolo" | "spotting" | "color"
  page: 1
}

export interface VisualFeatures {
  status: "ready" | "disabled" | "error"
  signature: boolean | null
  stamp: boolean | null
}

export interface DocumentData {
  type: string | null
  fields: Record<string, JsonValue>
  ocr_text: string
  coordinates: JsonValue[]
  image?: DocumentImage | null
  visual_features?: VisualFeatures | null
}

export interface Verification {
  status: string
  missing_fields: string[]
  issues: string[]
}

export interface AuthUser {
  email: string
  firstName: string
  lastName: string
  role: string
}

export interface LoginResult {
  success: boolean
  token: string
  user: AuthUser
}

export interface AnalysisResult {
  conversation_id: string
  answer: string
  sources: Source[]
  document: DocumentData | null
  verification: Verification | null
}
