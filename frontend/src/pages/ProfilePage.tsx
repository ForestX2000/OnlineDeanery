
import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  
  Mail,
  ShieldCheck,
  GraduationCap,
  FileText,
  Search,
  SlidersHorizontal,
  Clock3,
  CheckCircle2,
  XCircle,
  ArrowUpRight,
  
  Settings,
} from "lucide-react";
import { useAppStore } from "@/store/useAppStore";

type DocumentStatus = "Готово" | "В обработке" | "Отклонён";

type DocumentItem = {
  id: string;
  title: string;
  fileName: string;
  type: string;
  status: DocumentStatus;
  date: string;
  ownerEmail: string;
  ownerName: string;
};

const DEMO_DOCUMENTS: DocumentItem[] = [
  {
    id: "doc-001",
    title: "Справка об обучении",
    fileName: "spravka_ob_obuchenii.pdf",
    type: "Справка об обучении",
    status: "Готово",
    date: "12.10.2026",
    ownerEmail: "student@example.com",
    ownerName: "Иван Иванов",
  },
  {
    id: "doc-002",
    title: "Заявление на академический отпуск",
    fileName: "academic_leave.pdf",
    type: "Академический отпуск",
    status: "В обработке",
    date: "11.10.2026",
    ownerEmail: "student@example.com",
    ownerName: "Иван Иванов",
  },
  {
    id: "doc-003",
    title: "Справка о практике",
    fileName: "practice.pdf",
    type: "Справка о практике",
    status: "Готово",
    date: "10.10.2026",
    ownerEmail: "student@example.com",
    ownerName: "Иван Иванов",
  },
  {
    id: "doc-004",
    title: "Заявление на пересдачу",
    fileName: "retake.pdf",
    type: "Заявление",
    status: "В обработке",
    date: "09.10.2026",
    ownerEmail: "student2@example.com",
    ownerName: "Мария Петрова",
  },
  {
    id: "doc-005",
    title: "Справка об обучении",
    fileName: "study_certificate.pdf",
    type: "Справка об обучении",
    status: "Отклонён",
    date: "08.10.2026",
    ownerEmail: "student2@example.com",
    ownerName: "Мария Петрова",
  },
  {
    id: "doc-006",
    title: "Заявление на академический отпуск",
    fileName: "leave_request.pdf",
    type: "Академический отпуск",
    status: "Готово",
    date: "07.10.2026",
    ownerEmail: "student3@example.com",
    ownerName: "Алексей Смирнов",
  },
];

const STATUS_OPTIONS = [
  "Все статусы",
  "Готово",
  "В обработке",
  "Отклонён",
];

const TYPE_OPTIONS = [
  "Все типы",
  ...Array.from(new Set(DEMO_DOCUMENTS.map((doc) => doc.type))),
];

function statusStyles(status: DocumentStatus) {
  switch (status) {
    case "Готово":
      return "bg-emerald-50 text-emerald-700 ring-emerald-600/15";
    case "В обработке":
      return "bg-amber-50 text-amber-700 ring-amber-600/15";
    case "Отклонён":
      return "bg-red-50 text-red-700 ring-red-600/15";
  }
}

function StatusIcon({ status }: { status: DocumentStatus }) {
  if (status === "Готово") return <CheckCircle2 size={15} />;
  if (status === "В обработке") return <Clock3 size={15} />;
  return <XCircle size={15} />;
}

export default function ProfilePage() {
  const user = useAppStore((state) => state.user);
  const navigate = useNavigate();

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("Все статусы");
  const [typeFilter, setTypeFilter] = useState("Все типы");

  useEffect(() => {
    if (!user) navigate("/login", { replace: true });
  }, [user, navigate]);

  const isAdmin = user?.role === "admin";
  const visibleDocuments = useMemo(() => {
    if (!user) return [];

    return DEMO_DOCUMENTS.filter((doc) => {
      if (isAdmin) return true;
      return doc.ownerEmail.toLowerCase() === user.email.toLowerCase();
    });
  }, [user, isAdmin]);

  const filteredDocuments = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();

    return visibleDocuments.filter((doc) => {
      const matchesSearch =
        !normalizedSearch ||
        doc.title.toLowerCase().includes(normalizedSearch) ||
        doc.fileName.toLowerCase().includes(normalizedSearch) ||
        doc.ownerName.toLowerCase().includes(normalizedSearch) ||
        doc.ownerEmail.toLowerCase().includes(normalizedSearch);

      const matchesStatus =
        statusFilter === "Все статусы" || doc.status === statusFilter;

      const matchesType =
        typeFilter === "Все типы" || doc.type === typeFilter;

      return matchesSearch && matchesStatus && matchesType;
    });
  }, [visibleDocuments, search, statusFilter, typeFilter]);

  if (!user) return null;

  const completedCount = visibleDocuments.filter(
    (doc) => doc.status === "Готово",
  ).length;

  const processingCount = visibleDocuments.filter(
    (doc) => doc.status === "В обработке",
  ).length;

  return (
    <main className="min-h-screen bg-[#f4f7f4] px-4 py-8 text-slate-800 sm:px-6 lg:px-8">
      
      <div className="mx-auto max-w-7xl space-y-7">
        

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl bg-[#087b45] text-2xl font-bold text-white">
              {user.firstName?.[0] ?? ""}
              {user.lastName?.[0] ?? ""}
            </div>

            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-3">
                <h1 className="text-2xl font-bold text-slate-900">
                  {user.lastName} {user.firstName}
                </h1>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-[#087b45]">
                  {isAdmin ? (
                    <ShieldCheck size={16} />
                  ) : (
                    <GraduationCap size={16} />
                  )}
                  {isAdmin ? "Администратор" : "Студент"}
                </span>
              </div>

              <p className="mt-2 flex items-center gap-2 break-all text-sm text-slate-500">
                <Mail size={16} className="shrink-0" />
                {user.email}
              </p>
            </div>
          </div>
        </section>

        {isAdmin && (
          <section className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-500">Всего документов</p>
                <FileText className="text-[#087b45]" size={21} />
              </div>
              <p className="mt-3 text-3xl font-bold text-slate-900">
                {visibleDocuments.length}
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-500">Готово</p>
                <CheckCircle2 className="text-emerald-600" size={21} />
              </div>
              <p className="mt-3 text-3xl font-bold text-slate-900">
                {completedCount}
              </p>
            </div>

            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-500">В обработке</p>
                <Clock3 className="text-amber-600" size={21} />
              </div>
              <p className="mt-3 text-3xl font-bold text-slate-900">
                {processingCount}
              </p>
            </div>
          </section>
        )}

        <section>
          <div className="mb-5 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-2xl font-bold text-slate-900">
                {isAdmin ? "Все документы" : "Мои документы"}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                {isAdmin
                  ? "Поиск и управление документами пользователей"
                  : "Ваши загруженные документы и результаты обработки"}
              </p>
            </div>

            <span className="text-sm text-slate-500">
              Найдено: {filteredDocuments.length}
            </span>
          </div>

          <div className="mb-6 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_200px_220px]">
              <label className="relative block">
                <Search
                  size={18}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <input
                  value={search}
                  onChange={(event) => setSearch(event.target.value)}
                  placeholder={
                    isAdmin
                      ? "Поиск по документу или студенту..."
                      : "Поиск по названию документа..."
                  }
                  className="w-full rounded-xl border border-slate-200 bg-white py-3 pl-10 pr-3 text-sm outline-none transition focus:border-[#159957] focus:ring-4 focus:ring-emerald-50"
                />
              </label>

              <label className="relative">
                <span className="sr-only">Фильтр по статусу</span>
                <SlidersHorizontal
                  size={16}
                  className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
                />
                <select
                  value={statusFilter}
                  onChange={(event) => setStatusFilter(event.target.value)}
                  className="w-full appearance-none rounded-xl border border-slate-200 bg-white py-3 pl-9 pr-3 text-sm outline-none focus:border-[#159957]"
                >
                  {STATUS_OPTIONS.map((status) => (
                    <option key={status} value={status}>
                      {status}
                    </option>
                  ))}
                </select>
              </label>

              <label>
                <span className="sr-only">Фильтр по типу документа</span>
                <select
                  value={typeFilter}
                  onChange={(event) => setTypeFilter(event.target.value)}
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm outline-none focus:border-[#159957]"
                >
                  {TYPE_OPTIONS.map((type) => (
                    <option key={type} value={type}>
                      {type}
                    </option>
                  ))}
                </select>
              </label>
            </div>
          </div>

          {filteredDocuments.length > 0 ? (
            <div className="grid grid-cols-1 gap-5 md:grid-cols-2 xl:grid-cols-3">
              {filteredDocuments.map((doc) => (
                
                <button
                  key={doc.id}
                  type="button"
                  onClick={() => navigate(`/documents/${doc.id}`)}
                  className="group flex min-h-56 flex-col rounded-2xl border border-slate-200 bg-white p-5 text-left shadow-sm transition hover:-translate-y-1 hover:border-emerald-300 hover:shadow-lg focus:outline-none focus:ring-4 focus:ring-emerald-100"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-50 text-[#087b45] transition group-hover:bg-[#087b45] group-hover:text-white">
                      <FileText size={23} />
                    </div>
                    <span
                      className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1 ring-inset ${statusStyles(doc.status)}`}
                    >
                      <StatusIcon status={doc.status} />
                      {doc.status}
                    </span>
                  </div>

                  <h3 className="mt-5 line-clamp-2 text-lg font-semibold text-slate-900">
                    {doc.title}
                  </h3>

                  <p className="mt-2 truncate text-sm text-slate-500">
                    {doc.fileName}
                  </p>

                  <div className="mt-4 space-y-1 text-xs text-slate-500">
                    <p>{doc.type}</p>
                    <p>{doc.date}</p>
                    {isAdmin && (
                      <p className="truncate">
                        Студент: {doc.ownerName}
                      </p>
                    )}
                  </div>

                  <div className="mt-auto flex items-center justify-between border-t border-slate-100 pt-4">
                    <span className="text-sm font-semibold text-[#087b45]">
                      Открыть документ
                    </span>
                    <ArrowUpRight
                      size={18}
                      className="text-[#087b45] transition group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                    />
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-14 text-center">
              <FileText className="mx-auto text-slate-300" size={40} />
              <h3 className="mt-4 font-semibold text-slate-800">
                Документы не найдены
              </h3>
              <p className="mt-2 text-sm text-slate-500">
                Попробуйте изменить запрос или фильтры.
              </p>
              <button
                type="button"
                onClick={() => {
                  setSearch("");
                  setStatusFilter("Все статусы");
                  setTypeFilter("Все типы");
                }}
                className="mt-4 text-sm font-semibold text-[#087b45] hover:underline"
              >
                Сбросить фильтры
              </button>
            </div>
          )}
        </section>

        {isAdmin && (
          <div className="flex items-start gap-3 rounded-2xl border border-emerald-100 bg-emerald-50 p-4 text-sm leading-6 text-emerald-900">
            <Settings className="mt-0.5 shrink-0" size={19} />
            <p>
              Администратор может просматривать документы всех пользователей.
              В рабочей версии доступ к документам и административные права
              необходимо проверять на сервере.
            </p>
          </div>
        )}
      </div>
    </main>
  );
}
