import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { AnalysisResult } from "../../api"; // <-- ИМПОРТИРУЕМ правильный тип отсюда
import { canPreviewImage } from "../../api/highlights.ts";

export type DocumentType = "study_certificate" | "academic_leave" | "internship_certificate";
export type UserRole = "student" | "admin";

export interface User {
  email: string;
  firstName: string;
  lastName: string;
  role: UserRole;
}

interface AppState {
  step: "upload" | "processing" | "result"
  file: File | null
  docType: DocumentType | ""
  question: string
  result: AnalysisResult | null
  error: string | null
  step: "upload" | "processing" | "result";
  file: File | null;
  docType: DocumentType | "";
  question: string;
  result: AnalysisResult | null;
  error: string | null;
  preview: { url: string; name: string; conversationId: string } | null;

  setStep: (step: AppState["step"]) => void;
  setFormData: (data: { file: File | null; docType: DocumentType | ""; question: string }) => void;
  setResult: (result: AnalysisResult, sourceFile?: File | null) => void;
  setError: (error: string | null) => void;
  reset: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      user: null,
      login: (user) => set({ isAuthenticated: true, user }),
      logout: () => set((state) => {
        if (state.preview) URL.revokeObjectURL(state.preview.url);
        return { isAuthenticated: false, user: null,
          step: "upload", file: null, docType: "", question: "", result: null, error: null, preview: null };
      }),

      step: "upload", file: null, docType: "", question: "", result: null, error: null, preview: null,
      setStep: (step) => set({ step }),
      setFormData: (data) => set(data),
      setResult: (result, sourceFile) => set((state) => {
        let preview = state.preview;
        if (!result.document) preview = null;
        else if (sourceFile !== undefined) {
          preview = sourceFile && canPreviewImage(sourceFile)
            ? { url: URL.createObjectURL(sourceFile), name: sourceFile.name, conversationId: result.conversation_id }
            : null;
        } else if (preview?.conversationId !== result.conversation_id) preview = null;
        if (state.preview && state.preview !== preview) URL.revokeObjectURL(state.preview.url);
        return { result, preview, step: "result", error: null };
      }),
      setError: (error) => set({ error }),
      reset: () => set((state) => {
        if (state.preview) URL.revokeObjectURL(state.preview.url);
        return { step: "upload", file: null, docType: "", question: "", result: null, error: null, preview: null };
      }),
    }),
    {
      name: "online-deanery-storage",
      // zustand 5 не подставляет localStorage сам: без явного storage
      // persist молча ничего не сохраняет (только warning в консоль).
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        user: state.user,
        result: state.result,
      }),
    }
  )
);
