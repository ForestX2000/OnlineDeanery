import { create } from "zustand";
import { persist } from "zustand/middleware";

export type DocumentType = "study_certificate" | "academic_leave" | "internship_certificate";
export type UserRole = "student" | "admin";

export interface AnalysisResult {
  extracted_fields: Record<string, string>;
  answer: string;
  sources: { type: string; reference: string }[];
}

export interface User {
  email: string;
  firstName: string;
  lastName: string;
  role: UserRole;
}

interface AppState {
  isAuthenticated: boolean;
  user: User | null;
  login: (user: User) => void;
  logout: () => void;

  step: "upload" | "processing" | "result";
  file: File | null;
  docType: DocumentType | "";
  question: string;
  result: AnalysisResult | null;

  setStep: (step: AppState["step"]) => void;
  setFormData: (data: { file: File; docType: DocumentType; question: string }) => void;
  setResult: (result: AnalysisResult) => void;
  reset: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      user: null,
      login: (user) => set({ isAuthenticated: true, user }),
      logout: () => set({ 
        isAuthenticated: false, 
        user: null, 
        step: "upload", file: null, docType: "", question: "", result: null 
      }),

      step: "upload", file: null, docType: "", question: "", result: null,
      setStep: (step) => set({ step }),
      setFormData: (data) => set(data),
      setResult: (result) => set({ result, step: "result" }),
      reset: () => set({ step: "upload", file: null, docType: "", question: "", result: null }),
    }),
    {
      name: "online-deanery-storage",
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        user: state.user,
        result: state.result,
      }),
    }
  )
);