
import { useCallback, useState } from "react";
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
import { analyzeDocument, sendMessage, MAX_QUESTION_LENGTH } from "../../api";

const MAX_FILE_SIZE = 10 * 1024 * 1024;

const DOC_TYPES = [
  {
    value: "study_certificate",
    label: "Справка об обучении",
  },
  {
    value: "academic_leave",
    label: "Заявление на академический отпуск",
  },
  {
    value: "internship_certificate",
    label: "Справка о практике",
  },
] as const;

type DocumentType = (typeof DOC_TYPES)[number]["value"];

export default function DocumentUploader() {
  const navigate = useNavigate();

  const setFormData = useAppStore((state) => state.setFormData);
  const setResult = useAppStore((state) => state.setResult);
  const setStep = useAppStore((state) => state.setStep);

  const [file, setFile] = useState<File | null>(null);
  const [docType, setDocType] = useState<DocumentType | "">("");
  const [question, setQuestion] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  const onDrop = useCallback((files: File[]) => {
    setError("");
    if (files.length > 0) setFile(files[0]);
  }, []);

  const { getRootProps, getInputProps, isDragActive, open } =
    useDropzone({
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

        if (
          rejection.errors.some(
            (item) => item.code === "file-too-large",
          )
        ) {
          setError("Размер файла не должен превышать 10 МБ.");
        } else if (
          rejection.errors.some(
            (item) => item.code === "file-invalid-type",
          )
        ) {
          setError("Поддерживаются файлы PDF, PNG и JPG.");
        } else {
          setError("Не удалось загрузить файл. Попробуйте ещё раз.");
        }
      },
    });

  const handleSubmit = async (
    event: React.FormEvent<HTMLFormElement>,
  ) => {
    event.preventDefault();
    if (isLoading) return;
    setError("");

    if (!question.trim()) {
      setError("Напишите вопрос по вашему документу.");
      return;
    }

    setIsLoading(true);

    try {
      const formData = {
        file,
        docType,
        question: question.trim(),
      };

      setFormData(formData);
      setStep("processing");

      const result = file
        ? await analyzeDocument({ file, docType, question: formData.question })
        : await sendMessage(formData.question);

      setResult(result);
      navigate("/result");
    } catch (err) {
      console.error("Ошибка обработки документа:", err);
      setStep("upload");
      setError(
        err instanceof Error ? err.message : "Не удалось обработать документ. Попробуйте ещё раз.",
      );
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
    <main className="min-h-screen bg-[#f4f7f4] text-slate-800">
      <header className="border-b border-emerald-100 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <button
            type="button"
            onClick={() => navigate("/")}
            className="flex items-center gap-3 text-left"
          >
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#087b45] text-white shadow-sm">
              <FileText size={23} />
            </span>
            <span>
              <span className="block text-lg font-bold tracking-tight text-[#075c36]">
                Онлайн-деканат
              </span>
              <span className="block text-xs text-slate-500">
                Электронная обработка документов
              </span>
            </span>
          </button>

          <div className="hidden items-center gap-2 rounded-full bg-emerald-50 px-4 py-2 text-sm font-medium text-[#087b45] sm:flex">
            <ShieldCheck size={17} />
            Удобно и безопасно
          </div>
        </div>
      </header>

      <section className="mx-auto max-w-4xl px-5 py-10 sm:px-8 sm:py-14">
        <div className="mb-8">
          <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-emerald-100 bg-white px-3 py-1.5 text-sm font-medium text-[#087b45]">
            <span className="h-2 w-2 rounded-full bg-[#159957]" />
            Помощник по документам
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-slate-900 sm:text-4xl">
            Задайте вопрос
          </h1>

          <p className="mt-3 max-w-2xl text-base leading-7 text-slate-600">
            Задайте вопрос и при необходимости приложите документ.
            Система поможет разобрать содержание документа
            и подготовить ответ.
          </p>
        </div>

        <div className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-[0_16px_50px_rgba(15,60,35,0.07)]">
          <div className="h-1.5 bg-linear-to-r from-[#075c36] via-[#159957] to-[#b6d93c]" />

          <form onSubmit={handleSubmit} className="space-y-8 p-5 sm:p-9">
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
                onChange={(event) =>
                  setDocType(event.target.value as DocumentType | "")
                }
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3.5 text-sm outline-none transition focus:border-[#159957] focus:ring-4 focus:ring-emerald-50"
              >
                <option value="">Определить автоматически</option>
                {DOC_TYPES.map((item) => (
                  <option key={item.value} value={item.value}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <div className="mb-3 flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 font-bold text-[#087b45]">
                  2
                </span>
                <div>
                  <h2 className="font-semibold text-slate-900">
                    Файл документа (необязательно)
                  </h2>
                  <p className="text-sm text-slate-500">
                    PDF, PNG или JPG · до 10 МБ
                  </p>
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
                    {isDragActive ? (
                      <UploadCloud size={30} />
                    ) : (
                      <FileUp size={30} />
                    )}
                  </div>

                  <p className="mt-5 font-semibold text-slate-800">
                    {isDragActive
                      ? "Отпустите файл здесь"
                      : "Перетащите файл в эту область"}
                  </p>

                  <p className="mt-2 text-sm text-slate-500">
                    или выберите файл на устройстве
                  </p>

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
                    <p className="truncate font-semibold text-slate-800">
                      {file.name}
                    </p>
                    <p className="mt-1 text-sm text-slate-500">
                      {formatSize(file.size)}
                    </p>
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

            <div>
              <div className="mb-3 flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 font-bold text-[#087b45]">
                  3
                </span>
                <div>
                  <h2 className="font-semibold text-slate-900">
                    Ваш вопрос
                  </h2>
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

            {error && (
              <div
                role="alert"
                className="flex items-start gap-3 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700"
              >
                <AlertCircle className="mt-0.5 shrink-0" size={19} />
                <p>{error}</p>
              </div>
            )}

            <div className="rounded-xl bg-slate-50 p-4">
              <div className="flex items-start gap-3">
                <ShieldCheck
                  size={20}
                  className="mt-0.5 shrink-0 text-[#087b45]"
                />
                <p className="text-xs leading-5 text-slate-500">
                  Перед отправкой убедитесь, что загрузили нужный файл.
                  Не добавляйте документы с лишними персональными данными.
                  Обработка файла зависит от настроенного сервера.
                </p>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-[#087b45] px-5 py-4 font-semibold text-white shadow-[0_8px_20px_rgba(8,123,69,0.18)] transition hover:bg-[#075c36] focus:outline-none focus:ring-4 focus:ring-emerald-100 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isLoading ? (
                <>
                  <LoaderCircle size={20} className="animate-spin" />
                  Получаем ответ...
                </>
              ) : (
                <>
                  Отправить вопрос
                  <ArrowRight size={19} />
                </>
              )}
            </button>
          </form>
        </div>

        <p className="mt-5 text-center text-xs leading-5 text-slate-400">
          Онлайн-деканат · Электронный помощник для работы с документами
        </p>
      </section>
    </main>
  );
}
