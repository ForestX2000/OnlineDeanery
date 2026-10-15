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
        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-(--accent)/20 bg-(--surface) px-3 py-1.5 text-sm font-medium text-(--accent)">
          <span className="h-2 w-2 rounded-full bg-(--accent)" />
          Помощник по документам
        </div>

        <h1 className="text-3xl font-bold tracking-tight text-(--text-primary) sm:text-4xl">
          Задайте вопрос
        </h1>

        <p className="mt-3 max-w-2xl text-base leading-7 text-(--text-secondary)">
          Задайте вопрос и при необходимости приложите документ. Система поможет
          разобрать содержание документа и подготовить ответ.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Шаг 1: Тип документа */}
        <div>
          <div className="mb-3 flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-(--accent)/10 font-bold text-(--accent)">
              1
            </span>
            <div>
              <h2 className="font-semibold text-(--text-primary)">
                Тип документа (необязательно)
              </h2>
              <p className="text-sm text-(--text-secondary)">
                Выберите категорию или оставьте автоопределение
              </p>
            </div>
          </div>

          <select
            value={docType}
            onChange={(event) => setDocType(event.target.value as DocumentType | "")}
            className="w-full rounded-xl border border-(--border-color) bg-(--surface) px-4 py-3.5 text-sm text-(--text-primary) outline-none transition focus:border-(--accent) focus:ring-4 focus:ring-(--accent)/10 dark:bg-(--surface-muted)"
          >
            <option value="">Определить автоматически</option>
            {documentTypes.map((item) => (
              <option key={item.id} value={item.id}>
                {item.label}
              </option>
            ))}
          </select>
          {typeLoadError && <p role="status" className="mt-2 text-xs text-amber-700 dark:text-amber-400">{typeLoadError} Доступно автоопределение типа.</p>}
          {!file && docType && (
            <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">
              Тип «{documentTypes.find((item) => item.id === docType)?.label ?? docType}» применится к следующему файлу. Вопрос без файла идёт только по Положению.
            </p>
          )}
        </div>

        {/* Шаг 2: Файл документа */}
        <div>
          <div className="mb-3 flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-(--accent)/10 font-bold text-(--accent)">
              2
            </span>
            <div>
              <h2 className="font-semibold text-(--text-primary)">
                Файл документа (необязательно)
              </h2>
              <p className="text-sm text-(--text-secondary)">PDF, PNG или JPG · до 10 МБ</p>
            </div>
          </div>

          {!file ? (
            <div
              {...getRootProps()}
              className={`rounded-2xl border-2 border-dashed p-7 text-center transition sm:p-10 ${
                isDragActive
                  ? "border-(--accent) bg-(--accent)/10"
                  : "border-(--accent)/30 bg-(--surface-muted) hover:border-(--accent) hover:bg-(--accent)/5"
              }`}
            >
              <input {...getInputProps()} />
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-(--surface) text-(--accent) shadow-sm ring-1 ring-(--accent)/20">
                {isDragActive ? <UploadCloud size={30} /> : <FileUp size={30} />}
              </div>
              <p className="mt-5 font-semibold text-(--text-primary)">
                {isDragActive ? "Отпустите файл здесь" : "Перетащите файл в эту область"}
              </p>
              <p className="mt-2 text-sm text-(--text-secondary)">или выберите файл на устройстве</p>
              <button
                type="button"
                onClick={open}
                className="mt-5 inline-flex items-center gap-2 rounded-xl bg-(--accent) px-5 py-3 text-sm font-semibold text-white shadow-sm transition hover:bg-(--accent-hover) focus:outline-none focus:ring-4 focus:ring-(--accent)/20"
              >
                <UploadCloud size={17} />
                Выбрать файл
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-4 rounded-2xl border border-(--accent)/30 bg-(--accent)/5 p-4 dark:bg-(--accent)/10">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-(--surface) text-(--accent) shadow-sm">
                <FileText size={24} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold text-(--text-primary)">{file.name}</p>
                <p className="mt-1 text-sm text-(--text-secondary)">{formatSize(file.size)}</p>
                <p className="mt-1 flex items-center gap-1 text-xs font-medium text-(--accent)">
                  <CheckCircle2 size={14} />
                  Файл готов к обработке
                </p>
              </div>
              {/* Кнопка удаления файла — заметная и удобная */}
              <button
                type="button"
                onClick={removeFile}
                aria-label="Удалить файл"
                title="Удалить файл"
                className="group flex items-center gap-2 rounded-xl border border-rose-200 bg-white px-3 py-2 text-sm font-medium text-rose-600 transition hover:bg-rose-50 hover:text-rose-700 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-400 dark:hover:bg-rose-900/40 dark:hover:text-rose-300"
              >
                <Trash2 size={16} className="transition group-hover:scale-110" />
                <span className="hidden sm:inline">Удалить</span>
              </button>
            </div>
          )}
        </div>

        {/* Шаг 3: Вопрос */}
        <div>
          <div className="mb-3 flex items-center gap-3">
            <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-(--accent)/10 font-bold text-(--accent)">
              3
            </span>
            <div>
              <h2 className="font-semibold text-(--text-primary)">Ваш вопрос</h2>
              <p className="text-sm text-(--text-secondary)">
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
            className="w-full resize-y rounded-xl border border-(--border-color) bg-(--surface) px-4 py-3.5 text-sm leading-6 text-(--text-primary) outline-none transition placeholder:text-(--text-secondary)/50 focus:border-(--accent) focus:ring-4 focus:ring-(--accent)/10 dark:bg-(--surface-muted)"
          />
          <p className="mt-2 text-right text-xs text-(--text-secondary)">
            {question.length}/{MAX_QUESTION_LENGTH}
          </p>
        </div>

        {/* Ошибка */}
        {error && (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-400"
          >
            <AlertCircle className="mt-0.5 shrink-0" size={19} />
            <p>{error}</p>
          </div>
        )}

        {/* Кнопка отправки */}
        <button
          type="submit"
          disabled={isLoading}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-(--accent) px-5 py-4 font-semibold text-white shadow-lg shadow-(--accent)/20 transition hover:bg-(--accent-hover) focus:outline-none focus:ring-4 focus:ring-(--accent)/20 disabled:cursor-not-allowed disabled:opacity-60"
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
      <div className="mt-8 rounded-xl bg-(--surface-muted) p-4 border border-(--border-color)">
        <div className="flex items-start gap-3">
          <ShieldCheck size={20} className="mt-0.5 shrink-0 text-(--accent)" />
          <p className="text-xs leading-5 text-(--text-secondary)">
            Перед отправкой убедитесь, что загрузили нужный файл. Не добавляйте
            документы с лишними персональными данными.
          </p>
        </div>
      </div>
    </div>
  );
}