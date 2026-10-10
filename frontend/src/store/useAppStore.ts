import { create } from "zustand"

export type DocumentType =
  | "study_certificate"
  | "academic_leave"
  | "internship_certificate"

export interface AnalysisResult {
  extracted_fields: Record<string, string>
  answer: string
  sources: {
    type: string
    reference: string
  }[]
}

interface AppState {
  step: "upload" | "processing" | "result"
  file: File | null
  docType: DocumentType | ""
  question: string
  result: AnalysisResult | null

  setStep: (step: AppState["step"]) => void
  setFormData: (data: {
    file: File
    docType: DocumentType
    question: string
  }) => void
  setResult: (result: AnalysisResult) => void
  reset: () => void
}

export const useAppStore = create<AppState>((set) => ({
  step: "upload",
  file: null,
  docType: "",
  question: "",
  result: null,

  setStep: (step) => set({ step }),

  setFormData: (data) => set(data),

  setResult: (result) => set({ result, step: "result" }),

  reset: () => set({
    step: "upload",
    file: null,
    docType: "",
    question: "",
    result: null,
  }),
}))