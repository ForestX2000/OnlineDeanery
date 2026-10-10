import type {
  AnalysisResult,
  DocumentType,
} from "@/store/useAppStore"

interface AnalyzeParams {
  file: File
  docType: DocumentType
  question: string
}

const documentLabels: Record<DocumentType, string> = {
  study_certificate: "Справка об обучении",
  academic_leave: "Заявление на академический отпуск",
  internship_certificate: "Справка о практике",
}

export async function analyzeDocument({
  file,
  docType,
  question,
}: AnalyzeParams): Promise<AnalysisResult> {
  
  await new Promise((resolve) => setTimeout(resolve, 1500))

  return {
    extracted_fields: {
      document_type: documentLabels[docType],
      file_name: file.name,
      question,
      student_name: "Тестовые данные",
    },
    answer:
      "Это демонстрационный ответ. Настоящий анализ документа и проверка по нормативным актам появятся после подключения бэкенда.",
    sources: [],
  }
}