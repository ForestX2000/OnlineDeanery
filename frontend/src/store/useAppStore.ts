import { create } from "zustand"
import type { AnalysisResult, DocumentType } from "../../api"

interface AppState {
  step: "upload" | "processing" | "result"
  file: File | null
  docType: DocumentType | ""
  question: string
  result: AnalysisResult | null
  error: string | null

  setStep: (step: AppState["step"]) => void
  setFormData: (data: {
    file: File | null
    docType: DocumentType | ""
    question: string
  }) => void
  setResult: (result: AnalysisResult) => void
  setError: (error: string | null) => void
  reset: () => void
}

export const useAppStore = create<AppState>((set) => ({
  step: "upload",
  file: null,
  docType: "",
  question: "",
  result: null,
  error: null,

  setStep: (step) => set({ step }),

  setFormData: (data) => set(data),

  setResult: (result) => set({ result, step: "result", error: null }),
  setError: (error) => set({ error }),

  reset: () => set({
    step: "upload",
    file: null,
    docType: "",
    question: "",
    result: null,
    error: null,
  }),
}))
