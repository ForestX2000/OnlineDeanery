import { Link } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import DocumentUploader from "@/components/DocumentUploader";

export default function UploadPage() {
  return (
    <main className="min-h-screen bg-[#f4f7f4] px-5 py-10">
      <div className="mx-auto max-w-4xl">
        <Link
          to="/"
          className="mb-8 inline-flex items-center gap-2 text-sm text-[#1e293b]/70 hover:text-[#087b45]"
        >
          <ArrowLeft size={18} />
          На главную
        </Link>

        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[#1e293b] sm:text-4xl">
            Загрузка документа
          </h1>
          <p className="mt-3 text-[#1e293b]/70">
            Выбери тип документа, добавь файл и задай вопрос.
          </p>
        </div>

        <div className="rounded-3xl border border-[#1e293b]/10 bg-white p-5 shadow-sm sm:p-8">
          <DocumentUploader />
        </div>
      </div>
    </main>
  );
}