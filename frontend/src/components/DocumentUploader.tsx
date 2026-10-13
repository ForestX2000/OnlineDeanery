import { useCallback, useEffect, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  FileText,
  FileUp,
  LoaderCircle,
  ShieldCheck,
  Trash2,
  UploadCloud,
  AlertCircle,
} from "lucide-react";

import { useAppStore } from "../store/useAppStore";
import type { AnalysisResult, DocumentType } from "../../api";
import { analyzeDocument, getDocumentTypes, sendMessage, MAX_FILE_SIZE, MAX_QUESTION_LENGTH } from "../../api";

const pause = (ms: number) => new Promise<void>((resolve) => window.setTimeout(resolve, ms));

export default function DocumentUploader() {
  const navigate = useNavigate();

  const setResult = useAppStore((state) => state.setResult);
  const setStep = useAppStore((state) => state.setStep);
  const beginProcessing = useAppStore((state) => state.beginProcessing);
  const setProcessingStage = useAppStore((state) => state.setProcessingStage);
  const setProcessingDocument = useAppStore((state) => state.setProcessingDocument);
  const showProcessingField = useAppStore((state) => state.showProcessingField);
  const failProcessing = useAppStore((state) => state.failProcessing);
  const authToken = useAppStore((state) => state.authToken);
  const user = useAppStore((state) => state.user);

  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<DocumentType | "">("");
  const [documentTypes, setDocumentTypes] = useState<Array<{ id: string; label: string }>>([]);
  const [typeLoadError, setTypeLoadError] = useState("");
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    getDocumentTypes()
      .then((types) => { if (active) setDocumentTypes(types); })
      .catch((reason: unknown) => {
        if (active) setTypeLoadError(reason instanceof Error ? reason.message : "Не удалось загрузить типы документов.");
      });
    return () => { active = false; };
  }, []);

  const onDrop = useCallback((files: File[]) => {
    setError("");
    if (files.length > 0) setFile(files[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive, open } = useDropzone({
    onDrop,
    multiple: false,
    maxSize: MAX_FILE_SIZE,
    noClick: true,
    noKeyboard: true,
    accept: {
      "application/pdf": [".pdf"],
      "image/png": [".png"],
      "image/jpeg": [".jpg", ".jpeg"],
    },
    onDropRejected: (rejections) => {
      const rejection = rejections[0];
      if (!rejection) return;

      if (rejection.errors.some((item) => item.code === "file-too-large")) {
        setError("Размер файла не должен превышать 10 МБ.");
      } else if (rejection.errors.some((item) => item.code === "file-invalid-type")) {
        setError("Поддерживаются файлы PDF, PNG и JPG.");
      } else {
        setError("Не удалось загрузить файл. Попробуйте ещё раз.");
      }
    },
  });

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (isLoading) return;
    setError("");

    if (!question.trim()) {
      setError("Напишите вопрос по вашему документу.");
      return;
    }
    if (user && !authToken) {
      setError("Войдите в аккаунт заново, чтобы сохранять историю запросов.");
      navigate("/login");
      return;
    }

    setIsLoading(true);
    if (file) {
      beginProcessing(file, docType, question.trim());
      navigate("/result");
      let fieldAnimation = Promise.resolve();
      try {
        const result = await analyzeDocument({
          file,
          docType,
          question: question.trim(),
          token: authToken ?? undefined,
          onProgress: setProcessingStage,
          onFields: (document) => {
            setProcessingDocument(document);
            fieldAnimation = (async () => {
              for (const field of Object.keys(document.fields).filter((name) => !name.endsWith("_note"))) {
                await pause(140);
                showProcessingField(field);
              }
            })();
          },
        });
        await fieldAnimation;
        setResult(result as unknown as AnalysisResult, file);
      } catch (err) {
        await fieldAnimation;
        failProcessing(err instanceof Error ? err.message : "Не удалось обработать документ. Попробуйте ещё раз.");
      } finally {
        setIsLoading(false);
      }
      return;
    }

    setStep("processing");
    try {
      const result = await sendMessage(question.trim(), undefined, authToken ?? undefined);
      setResult(result as unknown as AnalysisResult);
      navigate("/result");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось получить ответ. Попробуйте ещё раз.");
      setStep("upload");
    } finally {
      setIsLoading(false);
    }
  };
  const removeFile = () => {
    setFile(null);
    setError("");
  };

  const formatSize = (size: number) => {
    if (size < 1024 * 1024) {
      return `${(size / 1024).toFixed(0)} КБ`;
    }
    return `${(size / (1024 * 1024)).toFixed(1)} МБ`;
  };

  return (
    <div className="mx-auto max-w-4xl px-5 py-10 sm:px-8 sm:py-14">
      <div className="mb-8">
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-1.5 text-sm font-medium text-[#087b45]">
          <span className="h-2 w-2 rounded-full bg-[#159957]" />
          Помощник по документам
        </div>

        <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
          Задайте вопрос
        </h1>

        <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
          Задайте вопрос и при необходимости приложите документ. Система поможет
          разобрать содержание документа и подготовить ответ.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Шаг 1: Тип документа */}
        <div>
          <div className="mb-3 flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 font-bold text-[#087b45]">
              1
            </span>
            <div>
              <h2 className="font-semibold text-slate-900">
                Тип документа (необязательно)
              </h2>
              <p className="text-sm text-slate-500">
                Выберите категорию или оставьте автоопределение
              </p>
            </div>
          </div>

          <select
            value={docType}
            onChange={(event) => setDocType(event.target.value as DocumentType | "")}
            className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3.5 text-sm outline-none transition focus:border-[#159957] focus:ring-4 focus:ring-emerald-50"
          >
            <option value="">Определить автоматически</option>
            {documentTypes.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
          {typeLoadError && <p role="status" className="mt-2 text-xs text-amber-700">{typeLoadError} Доступно автоопределение типа.</p>}
          {!file && docType && (
            <p className="mt-2 text-xs text-amber-700">
              Тип «{documentTypes.find((item) => item.id === docType)?.label ?? docType}» применится к следующему файлу. Вопрос без файла идёт только по Положению.
            </p>
          )}
        </div>

        {/* Шаг 2: Файл документа */}
        <div>
          <div className="mb-3 flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 font-bold text-[#087b45]">
              2
            </span>
            <div>
              <h2 className="font-semibold text-slate-900">
                Файл документа (необязательно)
              </h2>
              <p className="text-sm text-slate-500">PDF, PNG или JPG · до 10 МБ</p>
            </div>
          </div>

          {!file ? (
            <div
              {...getRootProps()}
              className={`rounded-2xl border-2 border-dashed p-7 text-center transition sm:p-10 ${
                isDragActive
                  ? "border-[#159957] bg-emerald-50"
                  : "border-emerald-200 bg-[#f9fcf9] hover:border-[#159957] hover:bg-emerald-50/60"
              }`}
            >
              <input {...getInputProps()} />
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-white text-[#087b45] shadow-sm ring-1 ring-emerald-100">
                {isDragActive ? <UploadCloud size={30} /> : <FileUp size={30} />}
              </div>
              <p className="mt-5 font-semibold text-slate-800">
                {isDragActive ? "Отпустите файл здесь" : "Перетащите файл в эту область"}
              </p>
              <p className="mt-2 text-sm text-slate-500">или выберите файл на устройстве</p>
              <button
                type="button"
                onClick={open}
                className="mt-5 inline-flex items-center gap-2 rounded-xl bg-[#087b45] px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-[#075c36] focus:outline-none focus:ring-4 focus:ring-emerald-100"
              >
                <UploadCloud size={17} />
                Выбрать файл
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-4 rounded-2xl border border-emerald-200 bg-emerald-50/60 p-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-white text-[#087b45] shadow-sm">
                <FileText size={24} />
              </div>
              <div className="min-w-0 flex-1">
                {/* TypeScript теперь знает, что file не может быть null здесь */}
                <p className="truncate font-semibold text-slate-800">{file.name}</p>
                <p className="mt-1 text-sm text-slate-500">{formatSize(file.size)}</p>
                <p className="mt-1 flex items-center gap-1 text-xs font-medium text-[#087b45]">
                  <CheckCircle2 size={14} />
                  Файл готов к обработке
                </p>
              </div>
              <button
                type="button"
                onClick={removeFile}
                aria-label="Удалить файл"
                className="rounded-lg p-2 text-slate-400 transition hover:bg-white hover:text-red-600"
              >
                <Trash2 size={19} />
              </button>
            </div>
          )}
        </div>

        {/* Шаг 3: Вопрос */}
        <div>
          <div className="mb-3 flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 font-bold text-[#087b45]">
              3
            </span>
            <div>
              <h2 className="font-semibold text-slate-900">Ваш вопрос</h2>
              <p className="text-sm text-slate-500">
                Уточните, что нужно узнать из документа
              </p>
            </div>
          </div>

          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Например: какие документы нужны для оформления академического отпуска?"
            rows={4}
            maxLength={MAX_QUESTION_LENGTH}
            className="w-full resize-y rounded-xl border border-slate-200 bg-white px-4 py-3.5 text-sm leading-6 outline-none transition placeholder:text-slate-400 focus:border-[#159957] focus:ring-4 focus:ring-emerald-50"
          />
          <p className="mt-2 text-right text-xs text-slate-400">
            {question.length}/{MAX_QUESTION_LENGTH}
          </p>
        </div>

        {/* Ошибка */}
        {error && (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
          >
            <AlertCircle className="mt-0.5 shrink-0" size={19} />
            <p>{error}</p>
          </div>
        )}

        {/* Кнопка отправки */}
        <button
          type="submit"
          disabled={isLoading}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#087b45] px-5 py-4 font-semibold text-white shadow-[0_8px_20px_rgba(8,123,69,0.18)] transition hover:bg-[#065c34] focus:outline-none focus:ring-4 focus:ring-[#087b45]/20 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isLoading ? (
            <>
              <LoaderCircle size={20} className="animate-spin" />
              Обрабатываем документ...
            </>
          ) : (
            <>
              Обработать документ
              <ArrowRight size={19} />
            </>
          )}
        </button>
      </form>

      {/* Подсказка безопасности */}
      <div className="mt-8 rounded-xl bg-[#f4f7f4] p-4">
        <div className="flex items-start gap-3">
          <ShieldCheck size={20} className="mt-0.5 shrink-0 text-[#087b45]" />
          <p className="text-xs leading-5 text-[#1e293b]/60">
            Перед отправкой убедитесь, что загрузили нужный файл. Не добавляйте
            документы с лишними персональными данными.
          </p>
        </div>
      </div>
    </div>
  );
}
