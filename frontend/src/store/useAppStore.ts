import { create } from "zustand";
import { createJSONStorage, persist } from "zustand/middleware";
import type { AnalysisResult, DocumentData, DocumentType } from "../../api";
import { canPreviewImage } from "../../api/highlights.ts";

export type UserRole = "student" | "admin";

export interface User {
  email: string;
  firstName: string;
  lastName: string;
  role: UserRole;
}

interface AppState {
  step: "upload" | "processing" | "result";
  file: File | null;
  docType: DocumentType | "";
  question: string;
  result: AnalysisResult | null;
  error: string | null;
  preview: { url: string; name: string; conversationId: string } | null;
  isProcessing: boolean;
  processingFileName: string;
  processingImage: { url: string; name: string } | null;
  processingDocument: DocumentData | null;
  processingVisibleFields: string[];
  processingStage: "ocr" | "extract" | "answer";
  processingDocType: DocumentType | "";
  processingError: string | null;
  isAuthenticated: boolean;
  authToken: string | null;
  user: User | null;

  setStep: (step: AppState["step"]) => void;
  setFormData: (data: { file: File | null; docType: DocumentType | ""; question: string }) => void;
  setResult: (result: AnalysisResult, sourceFile?: File | null) => void;
  beginProcessing: (file: File, docType: DocumentType | "", question: string) => void;
  setProcessingStage: (stage: "ocr" | "extract" | "answer") => void;
  setProcessingDocument: (document: DocumentData) => void;
  showProcessingField: (field: string) => void;
  failProcessing: (error: string) => void;
  setError: (error: string | null) => void;
  login: (user: User, token: string) => void;
  logout: () => void;
  reset: () => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      authToken: null,
      user: null,
      login: (user, authToken) => set({ isAuthenticated: true, user, authToken }),
      logout: () => set((state) => {
        if (state.preview) URL.revokeObjectURL(state.preview.url);
        if (state.processingImage) URL.revokeObjectURL(state.processingImage.url);
        return { isAuthenticated: false, authToken: null, user: null,
          step: "upload", file: null, docType: "", question: "", result: null, error: null, preview: null,
          isProcessing: false, processingFileName: "", processingImage: null, processingDocument: null,
          processingVisibleFields: [], processingStage: "ocr", processingDocType: "", processingError: null };
      }),

      step: "upload", file: null, docType: "", question: "", result: null, error: null, preview: null,
      isProcessing: false, processingFileName: "", processingImage: null, processingDocument: null,
      processingVisibleFields: [], processingStage: "ocr", processingDocType: "", processingError: null,
      setStep: (step) => set({ step }),
      setFormData: (data) => set(data),
      beginProcessing: (file, processingDocType, question) => set((state) => {
        if (state.preview) URL.revokeObjectURL(state.preview.url);
        if (state.processingImage) URL.revokeObjectURL(state.processingImage.url);
        const processingImage = canPreviewImage(file)
          ? { url: URL.createObjectURL(file), name: file.name }
          : null;
        return {
          step: "processing", docType: processingDocType, question, result: null, error: null, preview: null,
          isProcessing: true, processingFileName: file.name, processingImage, processingDocument: null,
          processingVisibleFields: [], processingStage: "ocr", processingDocType, processingError: null,
        };
      }),
      setProcessingStage: (processingStage) => set({ processingStage }),
      setProcessingDocument: (processingDocument) => set({ processingDocument, processingVisibleFields: [] }),
      showProcessingField: (field) => set((state) => state.processingVisibleFields.includes(field)
        ? state
        : { processingVisibleFields: [...state.processingVisibleFields, field] }),
      failProcessing: (processingError) => set({ isProcessing: false, processingError, step: "result" }),
      setResult: (result, sourceFile) => set((state) => {
        let preview = state.preview;
        if (!result.document) preview = null;
        else if (sourceFile !== undefined) {
          if (sourceFile && canPreviewImage(sourceFile)) {
            const processingImage = state.processingImage;
            preview = processingImage?.name === sourceFile.name
              ? { ...processingImage, conversationId: result.conversation_id }
              : { url: URL.createObjectURL(sourceFile), name: sourceFile.name, conversationId: result.conversation_id };
          } else preview = null;
        } else if (preview?.conversationId !== result.conversation_id) preview = null;
        if (state.preview && state.preview !== preview) URL.revokeObjectURL(state.preview.url);
        if (state.processingImage && state.processingImage.url !== preview?.url) {
          URL.revokeObjectURL(state.processingImage.url);
        }
        return {
          result, preview, step: "result", error: null, isProcessing: false, processingFileName: "",
          processingImage: null, processingDocument: null, processingVisibleFields: [], processingStage: "ocr", processingError: null,
        };
      }),
      setError: (error) => set({ error }),
      reset: () => set((state) => {
        if (state.preview) URL.revokeObjectURL(state.preview.url);
        if (state.processingImage) URL.revokeObjectURL(state.processingImage.url);
        return {
          step: "upload", file: null, docType: "", question: "", result: null, error: null, preview: null,
          isProcessing: false, processingFileName: "", processingImage: null, processingDocument: null,
          processingVisibleFields: [], processingStage: "ocr", processingDocType: "", processingError: null,
        };
      }),
    }),
    {
      name: "online-deanery-storage",
      // zustand 5 не подставляет localStorage сам: без явного storage
      // persist молча ничего не сохраняет (только warning в консоль).
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        authToken: state.authToken,
        user: state.user,
        result: state.result,
      }),
    }
  )
);
