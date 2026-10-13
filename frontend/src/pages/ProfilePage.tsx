import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  ChevronDown,
  CheckCircle2,
  Clock3,
  FileText,
  GraduationCap,
  Mail,
  RefreshCw,
  Search,
  ShieldCheck,
  UploadCloud,
} from "lucide-react";
import { ApiError, getRequestHistory } from "../../api";
import type { RequestHistoryItem } from "../../api";
import { useAppStore } from "@/store/useAppStore";

function requestStatus(status: string) {
  if (status === "resolved") return { label: "Завершён", style: "bg-emerald-50 text-emerald-700", icon: CheckCircle2 };
  if (status === "processing") return { label: "В обработке", style: "bg-amber-50 text-amber-700", icon: Clock3 };
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
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [reloadKey, setReloadKey] = useState(0);
  const [expandedItems, setExpandedItems] = useState<Set<number>>(() => new Set());

  useEffect(() => {
    if (!user) {
      navigate("/login", { replace: true });
      return;
    }
    if (!token) {
      setError("Сессия входа больше не действует. Войдите в аккаунт, чтобы открыть историю.");
      return;
    }

    let active = true;
    setLoading(true);
    setError(null);
    getRequestHistory(token)
      .then((history) => { if (active) setItems(history); })
      .catch((reason: unknown) => {
        if (!active) return;
        if (reason instanceof ApiError && reason.status === 401) {
          setError("Сессия входа истекла. Войдите в аккаунт заново.");
        } else {
          setError(reason instanceof Error ? reason.message : "Не удалось загрузить историю запросов.");
        }
      })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [user, token, navigate, reloadKey]);

  const isAdmin = user?.role === "admin";
  const filteredItems = useMemo(() => {
    const term = search.trim().toLocaleLowerCase("ru-RU");
    if (!term) return items;
    return items.filter((item) => [item.question, item.answer ?? "", item.user_name, item.user_email]
      .some((value) => value.toLocaleLowerCase("ru-RU").includes(term)));
  }, [items, search]);

  if (!user) return null;

  const resolvedCount = items.filter((item) => item.status === "resolved").length;
  const failedCount = items.filter((item) => item.status === "failed").length;
  const toggleExpanded = (requestId: number) => setExpandedItems((current) => {
    const next = new Set(current);
    if (next.has(requestId)) next.delete(requestId);
    else next.add(requestId);
    return next;
  });

  return (
    <main className="min-h-screen bg-[#f4f7f4] px-4 py-8 text-slate-800 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-6xl space-y-7">
        <header className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <button type="button" onClick={() => navigate("/")} className="flex w-fit items-center gap-3 text-left">
            <span className="flex h-11 w-11 items-center justify-center rounded-xl bg-[#087b45] text-white"><FileText size={23} /></span>
            <span>
              <span className="block text-lg font-bold text-[#075c36]">Онлайн-деканат</span>
              <span className="text-xs text-slate-500">Личный кабинет</span>
            </span>
          </button>
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
                <h1 className="text-2xl font-bold text-slate-900">{user.lastName} {user.firstName}</h1>
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
          <section className="grid gap-4 sm:grid-cols-3">
            <div className="rounded-2xl border border-slate-200 bg-white p-5">
              <p className="text-sm text-slate-500">Всего запросов</p>
              <p className="mt-3 text-3xl font-bold text-slate-900">{items.length}</p>
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
              <h2 className="text-2xl font-bold text-slate-900">{isAdmin ? "История запросов" : "Мои запросы"}</h2>
              <p className="mt-1 text-sm text-slate-500">
                {isAdmin ? "Запросы всех пользователей и ответы сервиса" : "Ваши вопросы и ответы по обработанным документам"}
              </p>
            </div>
            <div className="flex items-center gap-3 text-sm text-slate-500">
              <span>Найдено: {filteredItems.length}</span>
              <button type="button" onClick={() => setReloadKey((key) => key + 1)} disabled={loading}
                aria-label="Обновить историю" className="rounded-lg p-2 text-[#087b45] transition hover:bg-emerald-50 disabled:opacity-50">
                <RefreshCw size={18} className={loading ? "animate-spin" : ""} />
              </button>
            </div>
          </div>

          <label className="relative mb-5 block">
            <Search size={18} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
            <input value={search} onChange={(event) => setSearch(event.target.value)}
              placeholder={isAdmin ? "Поиск по вопросу, ответу или пользователю…" : "Поиск по вопросу или ответу…"}
              className="w-full rounded-xl border border-slate-200 bg-white py-3 pl-10 pr-3 text-sm outline-none transition focus:border-[#159957] focus:ring-4 focus:ring-emerald-50" />
          </label>

          {error && (
            <div role="alert" className="mb-5 flex items-center justify-between gap-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
              <span>{error}</span>
              {error.includes("Войдите") && <button type="button" onClick={() => navigate("/login")} className="shrink-0 font-semibold underline">Войти</button>}
            </div>
          )}

          {loading && items.length === 0 ? (
            <div className="rounded-2xl border border-slate-200 bg-white px-5 py-14 text-center text-slate-500">Загружаем историю запросов…</div>
          ) : error && items.length === 0 ? null : filteredItems.length ? (
            <div className="space-y-4">
              {filteredItems.map((item) => {
                const status = requestStatus(item.status);
                const StatusIcon = status.icon;
                return (
                  <article key={item.request_id} className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:border-[#087b45]/30 hover:shadow-md">
                    <button type="button" aria-expanded={expandedItems.has(item.request_id)} aria-controls={`request-details-${item.request_id}`}
                      onClick={() => toggleExpanded(item.request_id)}
                      className="flex w-full cursor-pointer flex-col gap-3 p-5 text-left outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#159957] sm:flex-row sm:items-center sm:justify-between">
                      <span className="min-w-0 flex-1">
                        <span className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm text-slate-500">
                          <time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
                          {isAdmin && <span className="truncate">{item.user_name} · {item.user_email}</span>}
                        </span>
                        <span className="mt-3 block line-clamp-2 whitespace-pre-wrap break-words font-semibold text-slate-800">{item.question}</span>
                      </span>
                      <span className="flex shrink-0 items-center justify-between gap-3 sm:justify-end">
                        <span className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium ${status.style}`}>
                          <StatusIcon size={14} /> {status.label}
                        </span>
                        <ChevronDown size={18} className={`text-slate-400 transition-transform duration-300 motion-reduce:transition-none ${expandedItems.has(item.request_id) ? "rotate-180" : ""}`} aria-hidden="true" />
                      </span>
                    </button>
                    <div id={`request-details-${item.request_id}`}
                      className={`grid transition-[grid-template-rows] duration-300 ease-in-out motion-reduce:transition-none ${expandedItems.has(item.request_id) ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}
                      aria-hidden={!expandedItems.has(item.request_id)}>
                      <div className="min-h-0 overflow-hidden">
                        <div className={`space-y-5 border-t border-slate-100 px-5 py-5 transition-opacity duration-200 motion-reduce:transition-none sm:px-6 ${expandedItems.has(item.request_id) ? "opacity-100" : "opacity-0"}`}>
                          <dl className="grid gap-4 text-sm sm:grid-cols-2">
                            <div>
                              <dt className="font-medium text-slate-500">Дата запроса</dt>
                              <dd className="mt-1 text-slate-800">{formatDate(item.created_at)}</dd>
                            </div>
                            <div>
                              <dt className="font-medium text-slate-500">Статус</dt>
                              <dd className="mt-1 inline-flex items-center gap-1.5 text-slate-800"><StatusIcon size={15} className={status.style.split(" ").filter((part) => part.startsWith("text-")).join(" ")} />{status.label}</dd>
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
                              : <p className="mt-2 text-sm text-slate-500">{item.status === "processing" ? "Запрос ещё обрабатывается." : "Ответ не сохранён."}</p>}
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
              <h3 className="mt-4 font-semibold text-slate-800">{search ? "Запросы не найдены" : "История пока пуста"}</h3>
              <p className="mt-2 text-sm text-slate-500">{search ? "Попробуйте изменить поисковый запрос." : "Обработанные документы и ответы появятся здесь."}</p>
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
