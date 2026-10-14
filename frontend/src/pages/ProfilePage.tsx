import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  FileText,
  GraduationCap,
  LoaderCircle,
  Mail,
  RefreshCw,
  Search,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";
import { ApiError, getDocumentTypes, getRequestHistory } from "../../api";
import type { DocumentTypeOption, RequestHistoryItem } from "../../api";
import { useAppStore } from "@/store/useAppStore";

type StatusFilter = "all" | "resolved" | "failed" | "processing";

function requestStatus(status: string) {
  if (status === "resolved") {
    return { label: "Завершено", style: "bg-emerald-50 text-emerald-700", icon: CheckCircle2 };
  }
  if (status === "processing") {
    return { label: "В обработке", style: "bg-amber-50 text-amber-700", icon: LoaderCircle };
  }
  return { label: "Ошибка", style: "bg-red-50 text-red-700", icon: AlertTriangle };
}

function formatDate(value: string) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? value
    : new Intl.DateTimeFormat("ru-RU", { dateStyle: "medium", timeStyle: "short" }).format(date);
}

export default function ProfilePage() {
  const user = useAppStore((state) => state.user);
  const token = useAppStore((state) => state.authToken);
  const navigate = useNavigate();
  const [items, setItems] = useState<RequestHistoryItem[]>([]);
  const [documentTypes, setDocumentTypes] = useState<DocumentTypeOption[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(() => new Set());

  const sessionExpired = user !== null && token === null;
  const visibleError = error ?? (sessionExpired ? "Сессия истекла. Войдите в аккаунт, чтобы открыть историю." : null);

  useEffect(() => {
    if (!user || !token) {
      if (!user) navigate("/login", { replace: true });
      return;
    }

    let active = true;
    // Флаги загрузки перед fetch в эффекте: штатный паттерн загрузки по [user, token, reloadKey],
    // каскадных рендеров нет — эффект не зависит от loading/error.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
    setError(null);
    getRequestHistory(token)
      .then((history) => { if (active) setItems(history); })
      .catch((reason: unknown) => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 401) {
          setError("Сессия истекла. Войдите в аккаунт заново.");
        } else {
          setError(reason instanceof Error ? reason.message : "Не удалось загрузить историю запросов.");
        }
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [user, token, navigate, reloadKey]);

  useEffect(() => {
    let active = true;
    getDocumentTypes()
      .then((types) => { if (active) setDocumentTypes(types); })
      .catch(() => { if (active) setDocumentTypes([]); });
    return () => { active = false; };
  }, []);

  const isAdmin = user?.role === "admin";
  const visibleItems = useMemo(() => {
    const term = search.trim().toLocaleLowerCase("ru-RU");
    const labels = new Map(documentTypes.map((item) => [item.id, item.label]));
    return items
      .filter((item) => statusFilter === "all" || item.status === statusFilter)
      .filter((item) => category === "all"
        || (category === "no-file" ? !item.document_type : item.document_type === category))
      .filter((item) => !term || [
        item.question,
        item.answer ?? "",
        item.user_name,
        item.user_email,
        item.document_type ? (labels.get(item.document_type) ?? item.document_type) : "Вопрос без файла",
      ].some((value) => value.toLocaleLowerCase("ru-RU").includes(term)));
  }, [items, search, category, statusFilter, documentTypes]);

  const categories = useMemo(() => {
    const labels = new Map(documentTypes.map((item) => [item.id, item.label]));
    for (const item of items) {
      if (item.document_type && !labels.has(item.document_type)) labels.set(item.document_type, item.document_type);
    }
    return Array.from(labels, ([id, label]) => ({ id, label }));
  }, [documentTypes, items]);

  if (!user) return null;

  const resolvedCount = items.filter((item) => item.status === "resolved").length;
  const failedCount = items.filter((item) => item.status === "failed").length;
  const processingCount = items.filter((item) => item.status === "processing").length;
  const toggleExpanded = (requestId: number) => setExpandedItems((current) => {
    const next = new Set(current);
    if (next.has(requestId)) next.delete(requestId);
    else next.add(requestId);
    return next;
  });

  return (
    <main className="min-h-screen bg-[#f4f7f4] px-4 py-8 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-7">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 className="text-3xl font-bold text-slate-900">{isAdmin ? "История запросов" : "Мои запросы"}</h1>
            <p className="mt-2 text-sm text-slate-500">
              {isAdmin ? "Запросы пользователей и результаты обработки" : "История обработки документов и ответов"}
            </p>
          </div>
          <button type="button" onClick={() => navigate("/upload")}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-[#087b45] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#075c36]">
            <UploadCloud size={18} /> Загрузить документ
          </button>
        </header>

        <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm sm:p-8">
          <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
            <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl bg-[#087b45] text-2xl font-bold text-white">
              {user.firstName?.[0] ?? ""}{user.lastName?.[0] ?? ""}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-3">
                <h2 className="text-2xl font-bold text-slate-900">{user.lastName} {user.firstName}</h2>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 text-sm font-medium text-[#087b45]">
                  {isAdmin ? <ShieldCheck size={16} /> : <GraduationCap size={16} />}
                  {isAdmin ? "Администратор" : "Студент"}
                </span>
              </div>
              <p className="mt-2 flex items-center gap-2 break-all text-sm text-slate-500"><Mail size={16} />{user.email}</p>
            </div>
          </div>
        </section>

        {isAdmin && (
          <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4" aria-label="Статистика запросов">
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <p className="text-sm text-slate-500">Всего обработанных запросов</p>
              <p className="mt-3 text-3xl font-bold text-slate-900">{resolvedCount + failedCount + processingCount}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <p className="text-sm text-slate-500">В обработке</p>
              <p className="mt-3 text-3xl font-bold text-amber-700">{processingCount}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <p className="text-sm text-slate-500">Завершено</p>
              <p className="mt-3 text-3xl font-bold text-emerald-700">{resolvedCount}</p>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <p className="text-sm text-slate-500">С ошибкой</p>
              <p className="mt-3 text-3xl font-bold text-red-700">{failedCount}</p>
            </div>
          </section>
        )}

        <section>
          <div className="mb-5 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <div>
              <h2 className="text-2xl font-bold text-slate-900">{isAdmin ? "Запросы пользователей" : "История обработки"}</h2>
              <p className="mt-1 text-sm text-slate-500">
                {isAdmin ? "Нажмите на запись, чтобы открыть вопрос и ответ" : "Запросы в обработке, завершённые проверки и обработки с ошибками"}
              </p>
            </div>
            <div className="flex items-center gap-3 text-sm text-slate-500">
              <span>Найдено: {visibleItems.length}</span>
              <button type="button" onClick={() => setReloadKey((key) => key + 1)} disabled={loading}
                aria-label="Обновить историю" className="rounded-lg p-2 text-[#087b45] transition hover:bg-emerald-50 disabled:opacity-50">
                <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
              </button>
            </div>
          </div>

          <div className="mb-5 grid gap-3 md:grid-cols-[minmax(0,1fr)_minmax(12rem,0.55fr)_minmax(10rem,0.4fr)]">
            <label className="relative block">
              <span className="sr-only">Поиск по истории</span>
              <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
              <input value={search} onChange={(event) => setSearch(event.target.value)}
                placeholder={isAdmin ? "Поиск по вопросу, ответу или пользователю…" : "Поиск по вопросу или ответу…"}
                className="w-full rounded-xl border border-slate-200 bg-white py-3 pl-10 pr-3 text-sm outline-none transition focus:border-[#159957] focus:ring-4 focus:ring-emerald-50" />
            </label>
            <label>
              <span className="sr-only">Категория файла</span>
              <select value={category} onChange={(event) => setCategory(event.target.value)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm outline-none focus:border-[#159957] focus:ring-4 focus:ring-emerald-50">
                <option value="all">Все категории файлов</option>
                <option value="no-file">Вопросы без файла</option>
                {categories.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}
              </select>
            </label>
            <label>
              <span className="sr-only">Результат обработки</span>
              <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
                className="w-full rounded-xl border border-slate-200 bg-white px-3 py-3 text-sm outline-none focus:border-[#159957] focus:ring-4 focus:ring-emerald-50">
                <option value="all">Все статусы</option>
                <option value="processing">В обработке</option>
                <option value="resolved">Завершено</option>
                <option value="failed">Ошибка</option>
              </select>
            </label>
          </div>

          {visibleError && (
            <div role="alert" className="mb-5 flex items-center justify-between gap-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <span>{visibleError}</span>
              {visibleError.includes("Войдите") && <button type="button" onClick={() => navigate("/login")} className="shrink-0 font-semibold underline">Войти</button>}
            </div>
          )}

          {loading && items.length === 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white px-5 py-14 text-center text-slate-500">Загружаем историю…</div>
          ) : visibleError && items.length === 0 ? null : visibleItems.length ? (
            <div className="space-y-4">
              {visibleItems.map((item) => {
                const status = requestStatus(item.status);
                const StatusIcon = status.icon;
                const expanded = expandedItems.has(item.request_id);
                const typeLabel = item.document_type
                  ? categories.find((type) => type.id === item.document_type)?.label ?? item.document_type
                  : "Вопрос без файла";
                return (
                  <article key={item.request_id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:border-[#087b45]/30 hover:shadow-md">
                    <button type="button" aria-expanded={expanded} aria-controls={"request-details-" + item.request_id}
                      onClick={() => toggleExpanded(item.request_id)}
                      className="flex w-full cursor-pointer flex-col gap-3 p-5 text-left outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#159957] sm:flex-row sm:items-center sm:justify-between">
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-500">
                          <time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
                          <span className="rounded-full bg-slate-100 px-2.5 py-1 text-xs">{typeLabel}</span>
                          {isAdmin && <span className="truncate">{item.user_name} · {item.user_email}</span>}
                        </span>
                        <span className="mt-3 block line-clamp-2 whitespace-pre-wrap break-words font-semibold text-slate-800">{item.question}</span>
                      </span>
                      <span className="flex shrink-0 items-center justify-between gap-3 sm:justify-end">
                        <span className={"inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium " + status.style}>
                          <StatusIcon size={14} /> {status.label}
                        </span>
                        <ChevronDown size={18} className={"text-slate-400 transition-transform duration-300 motion-reduce:transition-none " + (expanded ? "rotate-180" : "")} aria-hidden="true" />
                      </span>
                    </button>
                    <div id={"request-details-" + item.request_id}
                      className={"grid transition-[grid-template-rows] duration-300 ease-in-out motion-reduce:transition-none " + (expanded ? "grid-rows-[1fr]" : "grid-rows-[0fr]")}
                      aria-hidden={!expanded}>
                      <div className="min-h-0 overflow-hidden">
                        <div className={"space-y-5 border-t border-slate-100 px-5 py-5 transition-opacity duration-200 motion-reduce:transition-none sm:px-6 " + (expanded ? "opacity-100" : "opacity-0")}>
                          <dl className="grid gap-4 text-sm sm:grid-cols-2">
                            <div>
                              <dt className="font-medium text-slate-500">Дата запроса</dt>
                              <dd className="mt-1 text-slate-800">{formatDate(item.created_at)}</dd>
                            </div>
                            <div>
                              <dt className="font-medium text-slate-500">Тип файла</dt>
                              <dd className="mt-1 text-slate-800">{typeLabel}</dd>
                            </div>
                            <div>
                              <dt className="font-medium text-slate-500">Статус</dt>
                              <dd className="mt-1 inline-flex items-center gap-1.5 text-slate-800"><StatusIcon size={15} />{status.label}</dd>
                            </div>
                            {isAdmin && <div className="sm:col-span-2">
                              <dt className="font-medium text-slate-500">Пользователь</dt>
                              <dd className="mt-1 break-words text-slate-800">{item.user_name} · {item.user_email}</dd>
                            </div>}
                          </dl>
                          <div>
                            <h3 className="text-sm font-semibold text-[#087b45]">Вопрос</h3>
                            <p className="mt-2 whitespace-pre-wrap break-words text-slate-800">{item.question}</p>
                          </div>
                          <div>
                            <h3 className="text-sm font-semibold text-slate-500">Ответ</h3>
                            {item.answer
                              ? <p className="mt-2 whitespace-pre-wrap break-words leading-7 text-slate-700">{item.answer}</p>
                              : <p className="mt-2 text-sm text-slate-500">Ответ не сохранён.</p>}
                          </div>
                        </div>
                      </div>
                    </div>
                  </article>
                );
              })}
            </div>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-300 bg-white px-5 py-14 text-center">
              <FileText className="mx-auto text-slate-300" size={40} />
              <h3 className="mt-4 font-semibold text-slate-800">{search || category !== "all" || statusFilter !== "all" ? "Запросы не найдены" : "История пока пуста"}</h3>
              <p className="mt-2 text-sm text-slate-500">Измените фильтры или загрузите документ, чтобы начать обработку.</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
