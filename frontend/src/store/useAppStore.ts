import { create } from "zustand"

interface AppState {
  step: "upload" | "processing" | "result"
  setStep: (step: "upload" | "processing" | "result") => void
  // Сюда потом добавим данные документа
}

export const useAppStore = create<AppState>((set) => ({
  step: "upload",
  setStep: (step) => set({ step }),
}))