import { useCallback, useEffect, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useNavigate } from "react-router-dom";
import {
  ArrowRight,
  CheckCircle2,
  ChevronDown,
  FileText,
  FileUp,
  LoaderCircle,
  ShieldCheck,
  Trash2,
  UploadCloud,
  AlertCircle,
} from "lucide-react";

import { useAppStore } from "../store/useAppStore";
import type { DocumentType } from "../../api";
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
  
  // Состояние для кастомного dropdown
  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    getDocumentTypes()
      .then((types) => { if (active) setDocumentTypes(types); })
      .catch((reason: unknown) => {
        if (active) setTypeLoadError(reason instanceof Error ? reason.message : "Не удалось загрузить типы документов.");
      });
    return () => { active = false; };
  }, []);

  // Закрытие dropdown при клике вне его
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
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
        setResult(result, file);
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
      setResult(result);
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

  const selectedTypeLabel = documentTypes.find((item) => item.id === docType)?.label || "Определить автоматически";

  return (
    <div className="mx-auto max-w-4xl px-4 py-6 sm:px-6 sm:py-10 lg:px-8">
      <div className="mb-6 sm:mb-8">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-(--accent)/20 bg-(--surface) px-3 py-1.5 text-xs font-medium text-(--accent) sm:text-sm">
          <span className="h-2 w-2 rounded-full bg-(--accent)" />
          Помощник по документам
        </div>

        <h1 className="text-2xl font-bold tracking-tight text-(--text-primary) sm:text-3xl lg:text-4xl">
          Задайте вопрос
        </h1>

        <p className="mt-2 max-w-2xl text-sm leading-6 text-(--text-secondary) sm:text-base sm:leading-7">
          Задайте вопрос и при необходимости приложите документ. Система поможет
          разобрать содержание документа и подготовить ответ.
        </p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6 sm:space-y-8">
        {/* Шаг 1: Тип документа - КАСТОМНЫЙ DROPDOWN */}
        <div>
          <div className="mb-3 flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-(--accent)/10 text-sm font-bold text-(--accent) sm:h-9 sm:w-9 sm:text-base">
              1
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="text-sm font-semibold text-(--text-primary) sm:text-base">
                Тип документа
              </h2>
              <p className="text-xs text-(--text-secondary) sm:text-sm">
                Выберите категорию или оставьте автоопределение
              </p>
            </div>
          </div>

          {/* Кастомный dropdown */}
          <div ref={dropdownRef} className="relative">
            <button
              type="button"
              onClick={() => setIsDropdownOpen(!isDropdownOpen)}
              className="flex w-full items-center justify-between rounded-xl border border-(--border-color) bg-(--surface) px-4 py-3 text-left text-sm text-(--text-primary) transition hover:border-(--accent)/50 focus:border-(--accent) focus:outline-none focus:ring-4 focus:ring-(--accent)/10 dark:bg-(--surface-muted) sm:py-3.5"
              aria-expanded={isDropdownOpen}
              aria-haspopup="listbox"
            >
              <span className="truncate">{selectedTypeLabel}</span>
              <ChevronDown 
                className={`h-4 w-4 shrink-0 text-(--text-secondary) transition-transform ${isDropdownOpen ? "rotate-180" : ""}`} 
              />
            </button>

            {/* Dropdown список */}
            {isDropdownOpen && (
              <div className="absolute z-40 mt-2 w-full rounded-xl border border-(--border-color) bg-(--surface) shadow-lg dark:bg-(--surface-muted) sm:shadow-xl">
                <div className="max-h-60 overflow-y-auto py-1">
                  {/* Опция "Автоопределение" */}
                  <button
                    type="button"
                    onClick={() => {
                      setDocType("");
                      setIsDropdownOpen(false);
                    }}
                    className={`flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition hover:bg-(--accent)/5 ${
                      docType === "" ? "bg-(--accent)/10 text-(--accent)" : "text-(--text-primary)"
                    }`}
                  >
                    <div className={`flex h-5 w-5 items-center justify-center rounded-full border-2 ${
                      docType === "" ? "border-(--accent) bg-(--accent)" : "border-(--border-color)"
                    }`}>
                      {docType === "" && <CheckCircle2 className="h-3 w-3 text-white" />}
                    </div>
                    <span className="truncate">Определить автоматически</span>
                  </button>

                  {/* Остальные типы документов */}
                  {documentTypes.map((item) => (
                    <button
                      key={item.id}
                      type="button"
                      onClick={() => {
                        setDocType(item.id);
                        setIsDropdownOpen(false);
                      }}
                      className={`flex w-full items-center gap-3 px-4 py-2.5 text-left text-sm transition hover:bg-(--accent)/5 ${
                        docType === item.id ? "bg-(--accent)/10 text-(--accent)" : "text-(--text-primary)"
                      }`}
                    >
                      <div className={`flex h-5 w-5 items-center justify-center rounded-full border-2 ${
                        docType === item.id ? "border-(--accent) bg-(--accent)" : "border-(--border-color)"
                      }`}>
                        {docType === item.id && <CheckCircle2 className="h-3 w-3 text-white" />}
                      </div>
                      <span className="truncate">{item.label}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {typeLoadError && (
            <p role="status" className="mt-2 text-xs text-amber-700 dark:text-amber-400">
              {typeLoadError} Доступно автоопределение типа.
            </p>
          )}
          {!file && docType && (
            <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">
              Тип «{documentTypes.find((item) => item.id === docType)?.label ?? docType}» применится к следующему файлу.
            </p>
          )}
        </div>

        {/* Шаг 2: Файл документа */}
        <div>
          <div className="mb-3 flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-(--accent)/10 text-sm font-bold text-(--accent) sm:h-9 sm:w-9 sm:text-base">
              2
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="text-sm font-semibold text-(--text-primary) sm:text-base">
                Файл документа
              </h2>
              <p className="text-xs text-(--text-secondary) sm:text-sm">PDF, PNG или JPG · до 10 МБ</p>
            </div>
          </div>

          {!file ? (
            <div
              {...getRootProps()}
              className={`rounded-xl border-2 border-dashed p-4 text-center transition sm:rounded-2xl sm:p-7 lg:p-10 ${
                isDragActive
                  ? "border-(--accent) bg-(--accent)/10"
                  : "border-(--accent)/30 bg-(--surface-muted) hover:border-(--accent) hover:bg-(--accent)/5"
              }`}
            >
              <input {...getInputProps()} />
              <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-xl bg-(--surface) text-(--accent) shadow-sm ring-1 ring-(--accent)/20 sm:h-16 sm:w-16 sm:rounded-2xl">
                {isDragActive ? <UploadCloud size={24} className="sm:size-[30px]" /> : <FileUp size={24} className="sm:size-[30px]" />}
              </div>
              <p className="mt-3 text-sm font-semibold text-(--text-primary) sm:mt-5 sm:text-base">
                {isDragActive ? "Отпустите файл здесь" : "Перетащите файл"}
              </p>
              <p className="mt-1 text-xs text-(--text-secondary) sm:mt-2 sm:text-sm">или нажмите кнопку ниже</p>
              <button
                type="button"
                onClick={open}
                className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-(--accent) px-4 py-2.5 text-sm font-semibold text-white shadow-sm transition hover:bg-(--accent-hover) focus:outline-none focus:ring-4 focus:ring-(--accent)/20 sm:mt-5 sm:w-auto sm:px-5 sm:py-3"
              >
                <UploadCloud size={16} className="sm:size-[17px]" />
                Выбрать файл
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3 rounded-xl border border-(--accent)/30 bg-(--accent)/5 p-3 dark:bg-(--accent)/10 sm:gap-4 sm:rounded-2xl sm:p-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-(--surface) text-(--accent) shadow-sm sm:h-12 sm:w-12 sm:rounded-xl">
                <FileText size={20} className="sm:size-[24px]" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-semibold text-(--text-primary)">{file.name}</p>
                <p className="mt-0.5 text-xs text-(--text-secondary) sm:text-sm">{formatSize(file.size)}</p>
                <p className="mt-1 flex items-center gap-1 text-xs font-medium text-(--accent)">
                  <CheckCircle2 size={12} className="sm:size-[14px]" />
                  Готов к обработке
                </p>
              </div>
              <button
                type="button"
                onClick={removeFile}
                aria-label="Удалить файл"
                title="Удалить файл"
                className="group flex shrink-0 items-center gap-1.5 rounded-lg border border-rose-200 bg-white px-2.5 py-1.5 text-xs font-medium text-rose-600 transition hover:bg-rose-50 hover:text-rose-700 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-400 dark:hover:bg-rose-900/40 dark:hover:text-rose-300 sm:gap-2 sm:rounded-xl sm:px-3 sm:py-2 sm:text-sm"
              >
                <Trash2 size={14} className="transition group-hover:scale-110 sm:size-[16px]" />
                <span className="hidden sm:inline">Удалить</span>
              </button>
            </div>
          )}
        </div>

        {/* Шаг 3: Вопрос */}
        <div>
          <div className="mb-3 flex items-center gap-3">
            <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-(--accent)/10 text-sm font-bold text-(--accent) sm:h-9 sm:w-9 sm:text-base">
              3
            </span>
            <div className="min-w-0 flex-1">
              <h2 className="text-sm font-semibold text-(--text-primary) sm:text-base">Ваш вопрос</h2>
              <p className="text-xs text-(--text-secondary) sm:text-sm">
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
            className="w-full resize-y rounded-xl border border-(--border-color) bg-(--surface) px-3 py-3 text-sm leading-6 text-(--text-primary) outline-none transition placeholder:text-(--text-secondary)/50 focus:border-(--accent) focus:ring-4 focus:ring-(--accent)/10 dark:bg-(--surface-muted) sm:px-4 sm:py-3.5"
          />
          <p className="mt-2 text-right text-xs text-(--text-secondary)">
            {question.length}/{MAX_QUESTION_LENGTH}
          </p>
        </div>

        {/* Ошибка */}
        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-400 sm:gap-3 sm:rounded-xl sm:p-4"
          >
            <AlertCircle className="mt-0.5 shrink-0" size={16} />
            <p className="text-xs sm:text-sm">{error}</p>
          </div>
        )}

        {/* Кнопка отправки */}
        <button
          type="submit"
          disabled={isLoading}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-(--accent) px-5 py-3.5 text-sm font-semibold text-white shadow-lg shadow-(--accent)/20 transition hover:bg-(--accent-hover) focus:outline-none focus:ring-4 focus:ring-(--accent)/20 disabled:cursor-not-allowed disabled:opacity-60 sm:py-4 sm:text-base"
        >
          {isLoading ? (
            <>
              <LoaderCircle size={18} className="animate-spin sm:size-[20px]" />
              <span className="text-xs sm:text-sm">Обрабатываем документ...</span>
            </>
          ) : (
            <>
              <span className="text-xs sm:text-sm">Обработать документ</span>
              <ArrowRight size={16} className="sm:size-[19px]" />
            </>
          )}
        </button>
      </form>

      {/* Подсказка безопасности */}
      <div className="mt-6 rounded-lg border border-(--border-color) bg-(--surface-muted) p-3 sm:mt-8 sm:rounded-xl sm:p-4">
        <div className="flex items-start gap-2 sm:gap-3">
          <ShieldCheck size={16} className="mt-0.5 shrink-0 text-(--accent) sm:size-[20px]" />
          <p className="text-xs leading-5 text-(--text-secondary)">
            Перед отправкой убедитесь, что загрузили нужный файл. Не добавляйте
            документы с лишними персональными данными.
          </p>
        </div>
      </div>
    </div>
  );
}