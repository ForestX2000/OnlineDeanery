import type {
  AnalysisResult,
  DocumentType,
} from "@/store/useAppStore"
import { analyzeDocument as requestAnalysis } from "../../api"

interface AnalyzeParams {
  file: File
  docType: DocumentType
  question: string
}

export async function analyzeDocument({
  file,
  docType,
  question,
}: AnalyzeParams): Promise<AnalysisResult> {
  const result = await requestAnalysis({ file, docType, question })
  return {
    document_type: result.document?.type ?? null,
    extracted_fields: Object.fromEntries(
      Object.entries(result.document?.fields ?? {}).map(([key, value]) => [
        key,
        value == null || value === "" ? "не найдено"
          : typeof value === "boolean" ? (value ? "Да" : "Нет")
          : typeof value === "object" ? JSON.stringify(value) : String(value),
      ]),
    ),
    answer: result.answer,
    sources: result.sources,
  }
}
