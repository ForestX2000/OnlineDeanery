
import { useNavigate, useParams } from "react-router-dom";
import { ArrowLeft, FileText, ShieldCheck } from "lucide-react";

export default function DocumentDetailsPage() {
  const navigate = useNavigate();
  const { documentId } = useParams();

  return (
    <main className="min-h-screen bg-[#f4f7f4] px-4 py-10 sm:px-6">
      <div className="mx-auto max-w-3xl">
        <button
          type="button"
          onClick={() => navigate("/profile")}
          className="mb-6 inline-flex items-center gap-2 text-sm font-semibold text-[#087b45] hover:underline"
        >
          <ArrowLeft size={18} />
          Вернуться к документам
        </button>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-9">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-[#087b45]">
            <FileText size={28} />
          </div>

          <h1 className="mt-5 text-2xl font-bold text-slate-900">
            Информация о документе
          </h1>

          <p className="mt-2 text-sm text-slate-500">
            Здесь будут сведения о файле, его статусе и результате обработки.
          </p>

          <div className="mt-6 rounded-xl bg-[#f4f7f4] p-4">
            <p className="text-sm text-slate-500">Идентификатор документа</p>
            <p className="mt-1 break-all font-semibold text-slate-900">
              {documentId}
            </p>
          </div>

          <div className="mt-5 flex items-start gap-3 rounded-xl border border-emerald-100 bg-emerald-50 p-4 text-sm leading-6 text-emerald-900">
            <ShieldCheck size={20} className="mt-0.5 shrink-0" />
            Подробная информация появится после подключения хранилища
            документов и API.
          </div>
        </section>
      </div>
    </main>
  );
}
