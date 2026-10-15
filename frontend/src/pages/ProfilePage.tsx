import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  FileText,
  LoaderCircle,
  Mail,
  RefreshCw,
  Search,
  ShieldCheck,
  UserPlus,
  Pencil,
  Trash2,
} from "lucide-react";

import {
  getDocumentTypes,
  getRequestHistory,
  getUsers,
  updateUser,
  deleteUser,
} from "../../api";
import type {
  AdminUser,
  DocumentTypeOption,
  RequestHistoryItem,
  UpdateUserRequest,
} from "../../api";
import { useAppStore } from "@/store/useAppStore";

import EditUserModal from "../components/admin/EditUserModal";
import DeleteUserDialog from "../components/admin/DeleteUserDialog";

type StatusFilter = "all" | "resolved" | "failed";
type UserRole = "student" | "admin";

interface CreatedUser {
  user_id: number;
  username: string;
  email: string;
  role: string;
  created_at: string;
}

function getErrorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return "Произошла непредвиденная ошибка.";
}

function formatDate(date: string): string {
  const parsedDate = new Date(date);
  if (Number.isNaN(parsedDate.getTime())) return date;
  return parsedDate.toLocaleString("ru-RU", {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function ProfilePage() {
  const navigate = useNavigate();
  const user = useAppStore((state) => state.user);
  const token = useAppStore((state) => state.authToken);

  const [history, setHistory] = useState<RequestHistoryItem[]>([]);
  const [documentTypes, setDocumentTypes] = useState<DocumentTypeOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [expandedRequest, setExpandedRequest] = useState<number | null>(null);

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [usersError, setUsersError] = useState("");

  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [deletingUser, setDeletingUser] = useState<AdminUser | null>(null);

  const [username, setUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newRole, setNewRole] = useState<UserRole>("student");
  const [creatingUser, setCreatingUser] = useState(false);
  const [createError, setCreateError] = useState("");
  const [createSuccess, setCreateSuccess] = useState<CreatedUser | null>(null);

  const isAdmin = user?.role === "admin";
  const currentUserEmail = user?.email;
  const visibleUsers = users.filter((u) => u.email !== currentUserEmail);
  const currentUserId = users.find((u) => u.email === currentUserEmail)?.user_id;

  const displayName =
    [user?.firstName, user?.lastName].filter(Boolean).join(" ") ||
    user?.email ||
    "Пользователь";

  useEffect(() => {
    if (!user) navigate("/login", { replace: true });
  }, [user, navigate]);

  useEffect(() => {
    if (!user || !token) return;
    const authToken = token;
    let cancelled = false;
    async function loadHistory() {
      try {
        const result = await getRequestHistory(authToken);
        if (!cancelled) { setHistory(result); setError(""); }
      } catch (err) { if (!cancelled) setError(getErrorMessage(err)); }
      finally { if (!cancelled) setLoading(false); }
    }
    void loadHistory();
    return () => { cancelled = true; };
  }, [user, token]);

  useEffect(() => {
    let cancelled = false;
    async function loadDocumentTypes() {
      try {
        const result = await getDocumentTypes();
        if (!cancelled) setDocumentTypes(result);
      } catch { /* История останется доступной */ }
    }
    void loadDocumentTypes();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!isAdmin || !token) return;
    const authToken = token;
    let cancelled = false;
    async function loadUsers() {
      try {
        setUsersLoading(true);
        const result = await getUsers(authToken);
        if (!cancelled) { setUsers(result); setUsersError(""); }
      } catch (err) { if (!cancelled) setUsersError(getErrorMessage(err)); }
      finally { if (!cancelled) setUsersLoading(false); }
    }
    void loadUsers();
    return () => { cancelled = true; };
  }, [isAdmin, token]);

  const filteredHistory = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return history.filter((item) => {
      const matchesStatus = statusFilter === "all" || item.status === statusFilter;
      const matchesCategory = categoryFilter === "all" || item.document_type === categoryFilter;
      const searchableText = [
        item.question, item.answer, item.document_type, item.user_name, item.user_email,
      ].filter(Boolean).join(" ").toLowerCase();
      const matchesSearch = !normalizedSearch || searchableText.includes(normalizedSearch);
      return matchesStatus && matchesCategory && matchesSearch;
    });
  }, [history, search, statusFilter, categoryFilter]);

  const stats = useMemo(() => {
    const resolved = history.filter((item) => item.status === "resolved").length;
    const failed = history.filter((item) => item.status === "failed").length;
    return { total: history.length, resolved, failed };
  }, [history]);

  async function handleCreateUser(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setCreatingUser(true);
    setCreateError("");
    setCreateSuccess(null);

    if (!token) {
      setCreateError("Нет токена авторизации. Войдите в аккаунт заново.");
      setCreatingUser(false);
      return;
    }

    try {
      const response = await fetch(
        `${(import.meta.env.VITE_API_URL || "http://localhost:8000").replace(/\/+$/, "")}/api/admin/users`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({
            username: username.trim(), email: newEmail.trim(), password, role: newRole,
          }),
        }
      );
      const responseText = await response.text();
      let responseData: unknown = null;
      if (responseText) { try { responseData = JSON.parse(responseText); } catch { responseData = responseText; } }
      if (!response.ok) {
        const message =
          typeof responseData === "object" && responseData !== null && "detail" in responseData
            ? String(responseData.detail)
            : typeof responseData === "string" && responseData ? responseData : `Не удалось создать пользователя (${response.status}).`;
        throw new Error(message);
      }
      const createdUser = responseData as CreatedUser;
      setCreateSuccess(createdUser);
      setUsers((prev) => [...prev, {
        user_id: createdUser.user_id, username: createdUser.username,
        email: createdUser.email, role: createdUser.role, created_at: createdUser.created_at,
      }]);
      setUsername(""); setNewEmail(""); setPassword(""); setNewRole("student");
    } catch (err) { setCreateError(getErrorMessage(err)); }
    finally { setCreatingUser(false); }
  }

  async function handleUpdateUser(userId: number, data: UpdateUserRequest) {
    if (!token) throw new Error("Нет токена авторизации");
    const updated = await updateUser(userId, data, token);
    setUsers((prev) => prev.map((u) => (u.user_id === userId ? updated : u)));
    setEditingUser(null);
  }

  async function handleDeleteUser(userId: number) {
    if (!token) throw new Error("Нет токена авторизации");
    await deleteUser(userId, token);
    setUsers((prev) => prev.filter((u) => u.user_id !== userId));
    setDeletingUser(null);
  }

  if (!user) return null;

  if (!token) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-10">
        <div className="flex items-start gap-3 rounded-xl border border-(--accent)/20 bg-(--accent)/10 p-4 text-(--accent)">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <h2 className="font-semibold">Требуется авторизация</h2>
            <p className="mt-1 text-sm">Сессия отсутствует или истекла. Войдите в аккаунт.</p>
            <button type="button" onClick={() => navigate("/login")}
              className="mt-3 rounded-lg bg-(--accent) px-4 py-2 text-sm font-medium text-white transition hover:bg-(--accent-hover)">
              Перейти ко входу
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl space-y-6 px-3 py-6 sm:space-y-8 sm:px-4 sm:py-8 lg:px-8">
      {/* Заголовок профиля */}
      <section className="rounded-2xl border border-(--border-color) bg-(--surface) p-4 shadow-sm sm:p-6">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-(--accent)/10 text-(--accent) shrink-0 sm:h-14 sm:w-14">
              <ShieldCheck className="h-6 w-6 sm:h-7 sm:w-7" />
            </div>
            <div className="min-w-0">
              <h1 className="text-xl font-bold text-(--text-primary) truncate sm:text-2xl">Личный кабинет</h1>
              <p className="mt-0.5 text-sm text-(--text-secondary) truncate sm:text-base">{displayName}</p>
              <p className="mt-1 flex items-center gap-2 text-xs text-(--text-secondary) sm:text-sm">
                <Mail className="h-3.5 w-3.5 shrink-0 sm:h-4 sm:w-4" />
                <span className="truncate">{user.email}</span>
              </p>
            </div>
          </div>
          <span className="inline-flex w-fit items-center rounded-full bg-(--accent)/10 px-3 py-1.5 text-xs font-medium text-(--accent) sm:text-sm">
            {isAdmin ? "Администратор" : "Студент"}
          </span>
        </div>
      </section>

      {/* Статистика */}
      {isAdmin && (
        <section>
          <h2 className="mb-3 text-lg font-semibold text-(--text-primary) sm:mb-4 sm:text-xl">Статистика запросов</h2>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3 sm:gap-4">
            <StatCard title="Всего запросов" value={stats.total} className="bg-(--accent)/10 text-(--accent)" />
            <StatCard title="Успешных" value={stats.resolved} className="bg-(--accent)/10 text-(--accent)" />
            <StatCard title="С ошибками" value={stats.failed} className="bg-rose-50 text-rose-700 dark:bg-rose-900/20 dark:text-rose-400" />
          </div>
        </section>
      )}

      {/* Управление пользователями */}
      {isAdmin && (
        <section className="rounded-2xl border border-(--border-color) bg-(--surface) p-4 shadow-sm sm:p-6">
          <div className="mb-4 flex items-center gap-3 sm:mb-5">
            <div className="rounded-xl bg-(--accent)/10 p-2 text-(--accent)">
              <UserPlus className="h-5 w-5" />
            </div>
            <div className="min-w-0">
              <h2 className="text-lg font-semibold text-(--text-primary) sm:text-xl">Управление пользователями</h2>
              <p className="mt-0.5 text-xs text-(--text-secondary) sm:text-sm">Добавление, редактирование и удаление</p>
            </div>
          </div>

          <form onSubmit={handleCreateUser} className="space-y-3 sm:space-y-4">
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 sm:gap-4">
              <FormField label="Имя пользователя">
                <input required minLength={2} value={username} onChange={(e) => setUsername(e.target.value)}
                  placeholder="Например, ivan_ivanov" autoComplete="username"
                  className="w-full rounded-lg border border-(--border-color) bg-(--surface) px-3 py-2.5 text-sm text-(--text-primary) outline-none transition focus:border-(--accent) focus:ring-2 focus:ring-(--accent)/20 dark:bg-(--surface-muted) sm:text-base" />
              </FormField>
              <FormField label="Электронная почта">
                <input required type="email" value={newEmail} onChange={(e) => setNewEmail(e.target.value)}
                  placeholder="student@example.com" autoComplete="email"
                  className="w-full rounded-lg border border-(--border-color) bg-(--surface) px-3 py-2.5 text-sm text-(--text-primary) outline-none transition focus:border-(--accent) focus:ring-2 focus:ring-(--accent)/20 dark:bg-(--surface-muted) sm:text-base" />
              </FormField>
              <FormField label="Пароль">
                <input required minLength={8} type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                  placeholder="Не менее 8 символов" autoComplete="new-password"
                  className="w-full rounded-lg border border-(--border-color) bg-(--surface) px-3 py-2.5 text-sm text-(--text-primary) outline-none transition focus:border-(--accent) focus:ring-2 focus:ring-(--accent)/20 dark:bg-(--surface-muted) sm:text-base" />
              </FormField>
              <FormField label="Роль">
                <select value={newRole} onChange={(e) => setNewRole(e.target.value as UserRole)}
                  className="w-full rounded-lg border border-(--border-color) bg-(--surface) px-3 py-2.5 text-sm text-(--text-primary) outline-none transition focus:border-(--accent) focus:ring-2 focus:ring-(--accent)/20 dark:bg-(--surface-muted) sm:text-base">
                  <option value="student">Студент</option>
                  <option value="admin">Администратор</option>
                </select>
              </FormField>
            </div>

            {createError && (
              <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-400">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>{createError}</span>
              </div>
            )}
            {createSuccess && (
              <div className="flex items-start gap-2 rounded-lg border border-(--accent)/20 bg-(--accent)/10 p-3 text-sm text-(--accent)">
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <p className="font-semibold">Пользователь создан</p>
                  <p className="mt-1">{createSuccess.username} — {createSuccess.email}</p>
                  <p className="mt-1">Роль: {createSuccess.role}. ID: {createSuccess.user_id}</p>
                </div>
              </div>
            )}

            <button type="submit" disabled={creatingUser}
              className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-(--accent) px-5 py-2.5 font-medium text-white transition hover:bg-(--accent-hover) disabled:cursor-not-allowed disabled:opacity-60 sm:w-auto">
              {creatingUser ? <LoaderCircle className="h-4 w-4 animate-spin" /> : <UserPlus className="h-4 w-4" />}
              {creatingUser ? "Создание..." : "Создать пользователя"}
            </button>
          </form>

          {/* Таблица/Карточки пользователей */}
          <div className="mt-6 border-t border-(--border-color) pt-4 sm:mt-8 sm:pt-6">
            <h3 className="mb-3 text-base font-semibold text-(--text-primary) sm:mb-4 sm:text-lg">Зарегистрированные пользователи</h3>

            {usersLoading ? (
              <div className="flex items-center justify-center gap-2 rounded-xl border border-(--border-color) bg-(--surface-muted) p-6 text-(--text-secondary)">
                <LoaderCircle className="h-5 w-5 animate-spin" /> Загрузка списка...
              </div>
            ) : usersError ? (
              <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-400">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" /><span>Не удалось загрузить список: {usersError}</span>
              </div>
            ) : users.length === 0 ? (
              <div className="rounded-xl border border-dashed border-(--border-color) bg-(--surface-muted) p-6 text-center text-sm text-(--text-secondary)">
                Пользователи пока не созданы
              </div>
            ) : (
              <>
                {/* 📱 КАРТОЧКИ НА МОБИЛЬНЫХ */}
                <div className="space-y-3 sm:hidden">
                  {visibleUsers.map((u, index) => (
                    <div key={u.user_id} className="rounded-xl border border-(--border-color) bg-(--surface-muted) p-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-(--accent)/10 text-sm font-semibold text-(--accent)">
                            {index + 1}
                          </div>
                          <div className="min-w-0">
                            <p className="truncate text-sm font-semibold text-(--text-primary)">{u.username}</p>
                            <p className="truncate text-xs text-(--text-secondary)">{u.email}</p>
                          </div>
                        </div>
                        <span className={`shrink-0 inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                          u.role === "admin" ? "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400" : "bg-(--accent)/10 text-(--accent)"
                        }`}>
                          {u.role === "admin" ? "Админ" : "Студент"}
                        </span>
                      </div>
                      <div className="mt-3 flex justify-end gap-2 border-t border-(--border-color) pt-3">
                        <button onClick={() => setEditingUser(u)}
                          className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-(--text-secondary) transition hover:bg-(--accent)/10 hover:text-(--accent)">
                          <Pencil className="h-3.5 w-3.5" /> Редактировать
                        </button>
                        <button onClick={() => setDeletingUser(u)}
                          className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs font-medium text-(--text-secondary) transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-900/30 dark:hover:text-rose-400">
                          <Trash2 className="h-3.5 w-3.5" /> Удалить
                        </button>
                      </div>
                    </div>
                  ))}
                </div>

                {/* 💻 ТАБЛИЦА НА DESKTOP */}
                <div className="hidden overflow-hidden rounded-xl border border-(--border-color) sm:block">
                  <table className="min-w-full divide-y divide-(--border-color)">
                    <thead className="bg-(--surface-muted)">
                      <tr>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-(--text-secondary)">№</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-(--text-secondary)">Имя</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-(--text-secondary)">Email</th>
                        <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-(--text-secondary)">Роль</th>
                        <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-(--text-secondary)">Действия</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-(--border-color) bg-(--surface)">
                      {visibleUsers.map((u, index) => (
                        <tr key={u.user_id} className="transition-colors hover:bg-(--surface-muted)">
                          <td className="whitespace-nowrap px-4 py-3 text-sm text-(--text-secondary)">{index + 1}</td>
                          <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-(--text-primary)">{u.username}</td>
                          <td className="whitespace-nowrap px-4 py-3 text-sm text-(--text-secondary)">{u.email}</td>
                          <td className="whitespace-nowrap px-4 py-3 text-sm">
                            <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                              u.role === "admin" ? "bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400" : "bg-(--accent)/10 text-(--accent)"
                            }`}>
                              {u.role === "admin" ? "Админ" : "Студент"}
                            </span>
                          </td>
                          <td className="whitespace-nowrap px-4 py-3 text-right">
                            <div className="inline-flex items-center justify-end gap-2">
                              <button onClick={() => setEditingUser(u)}
                                className="rounded-lg p-2 text-(--text-secondary) transition hover:bg-(--accent)/10 hover:text-(--accent)" title="Редактировать">
                                <Pencil className="h-4 w-4" />
                              </button>
                              <button onClick={() => setDeletingUser(u)}
                                className="rounded-lg p-2 text-(--text-secondary) transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-900/30 dark:hover:text-rose-400" title="Удалить">
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            )}
          </div>
        </section>
      )}

      {/* История запросов */}
      <section className="space-y-4 sm:space-y-5">
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between sm:gap-3">
          <div className="min-w-0">
            <h2 className="text-lg font-semibold text-(--text-primary) sm:text-xl">История запросов</h2>
            <p className="mt-0.5 text-xs text-(--text-secondary) sm:text-sm">Все ваши обращения и результаты обработки документов</p>
          </div>
          <button type="button" onClick={() => window.location.reload()}
            className="inline-flex w-full items-center justify-center gap-2 rounded-lg border border-(--border-color) bg-(--surface) px-3 py-2 text-sm font-medium text-(--text-primary) transition hover:bg-(--surface-muted) sm:w-auto">
            <RefreshCw className="h-4 w-4" /> Обновить
          </button>
        </div>

        <div className="grid grid-cols-1 gap-3 rounded-2xl border border-(--border-color) bg-(--surface) p-3 shadow-sm sm:grid-cols-3 sm:p-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-(--text-secondary)" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Поиск..."
              className="w-full rounded-lg border border-(--border-color) bg-(--surface) py-2.5 pl-9 pr-3 text-sm text-(--text-primary) outline-none transition focus:border-(--accent) focus:ring-2 focus:ring-(--accent)/20 dark:bg-(--surface-muted)" />
          </div>
          <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value as StatusFilter)}
            className="rounded-lg border border-(--border-color) bg-(--surface) px-3 py-2.5 text-sm text-(--text-primary) outline-none transition focus:border-(--accent) dark:bg-(--surface-muted)">
            <option value="all">Все статусы</option>
            <option value="resolved">Успешные</option>
            <option value="failed">С ошибками</option>
          </select>
          <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}
            className="rounded-lg border border-(--border-color) bg-(--surface) px-3 py-2.5 text-sm text-(--text-primary) outline-none transition focus:border-(--accent) dark:bg-(--surface-muted)">
            <option value="all">Все типы документов</option>
            {documentTypes.map((type) => <option key={type.id} value={type.label}>{type.label}</option>)}
          </select>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-3 rounded-2xl border border-(--border-color) bg-(--surface) p-10 text-(--text-secondary)">
            <LoaderCircle className="h-5 w-5 animate-spin" /> Загружаем историю запросов...
          </div>
        ) : error ? (
          <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-700 dark:border-rose-800 dark:bg-rose-900/20 dark:text-rose-400">
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <div><p className="font-semibold">Не удалось загрузить историю</p><p className="mt-1 text-sm">{error}</p></div>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-(--border-color) bg-(--surface) p-8 text-center sm:p-10">
            <FileText className="mx-auto h-10 w-10 text-(--text-secondary)" />
            <h3 className="mt-3 font-semibold text-(--text-primary)">Запросы не найдены</h3>
            <p className="mt-1 text-sm text-(--text-secondary)">Попробуйте изменить фильтры или выполнить новый запрос.</p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredHistory.map((item) => {
              const expanded = expandedRequest === item.request_id;
              const succeeded = item.status === "resolved";
              return (
                <article key={item.request_id} className="overflow-hidden rounded-2xl border border-(--border-color) bg-(--surface) shadow-sm">
                  <button type="button" onClick={() => setExpandedRequest(expanded ? null : item.request_id)}
                    aria-expanded={expanded}
                    className="flex w-full items-center justify-between gap-3 p-3 text-left transition hover:bg-(--surface-muted) sm:gap-4 sm:p-4">
                    <div className="flex min-w-0 items-start gap-3">
                      <div className={`mt-0.5 rounded-xl p-2 shrink-0 ${succeeded ? "bg-(--accent)/10 text-(--accent)" : "bg-rose-50 text-rose-700 dark:bg-rose-900/20 dark:text-rose-400"}`}>
                        {succeeded ? <CheckCircle2 className="h-4 w-4 sm:h-5 sm:w-5" /> : <AlertCircle className="h-4 w-4 sm:h-5 sm:w-5" />}
                      </div>
                      <div className="min-w-0">
                        <h3 className="truncate text-sm font-semibold text-(--text-primary) sm:text-base">{item.document_type || "Запрос"}</h3>
                        <p className="mt-0.5 line-clamp-2 text-xs text-(--text-secondary) sm:text-sm">{item.question || "Без текста запроса"}</p>
                        <p className="mt-1 text-xs text-(--text-secondary)">{formatDate(item.created_at)}</p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span className={`hidden rounded-full px-2.5 py-1 text-xs font-medium sm:inline-flex ${
                        succeeded ? "bg-(--accent)/10 text-(--accent)" : "bg-rose-50 text-rose-700 dark:bg-rose-900/20 dark:text-rose-400"
                      }`}>
                        {succeeded ? "Успешно" : "Ошибка"}
                      </span>
                      <ChevronDown className={`h-5 w-5 text-(--text-secondary) transition-transform ${expanded ? "rotate-180" : ""}`} />
                    </div>
                  </button>

                  {expanded && (
                    <div className="space-y-3 border-t border-(--border-color) bg-(--surface-muted) p-3 sm:space-y-4 sm:p-4">
                      {isAdmin && (
                        <div className="grid grid-cols-1 gap-2 text-xs sm:grid-cols-2 sm:text-sm">
                          <p className="text-(--text-secondary)"><span className="font-medium text-(--text-primary)">Пользователь:</span> {item.user_name || "Не указан"}</p>
                          <p className="text-(--text-secondary)"><span className="font-medium text-(--text-primary)">Email:</span> {item.user_email || "Не указан"}</p>
                        </div>
                      )}
                      <div>
                        <h4 className="text-xs font-semibold text-(--text-primary) sm:text-sm">Запрос</h4>
                        <p className="mt-1 whitespace-pre-wrap text-xs text-(--text-secondary) sm:text-sm">{item.question || "Нет текста запроса"}</p>
                      </div>
                      <div>
                        <h4 className="text-xs font-semibold text-(--text-primary) sm:text-sm">Ответ системы</h4>
                        <p className="mt-1 whitespace-pre-wrap text-xs text-(--text-secondary) sm:text-sm">{item.answer || "Ответ отсутствует"}</p>
                      </div>
                      <p className="text-xs text-(--text-secondary)">ID запроса: {item.request_id}</p>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}

        {!loading && !error && filteredHistory.length > 0 && (
          <p className="text-center text-xs text-(--text-secondary) sm:text-sm">
            Показано запросов: {filteredHistory.length} из {history.length}
          </p>
        )}
      </section>

      {/* МОДАЛЬНЫЕ ОКНА */}
      {editingUser && (
        <EditUserModal user={editingUser} currentUserId={currentUserId}
          onClose={() => setEditingUser(null)} onSave={handleUpdateUser} />
      )}
      {deletingUser && (
        <DeleteUserDialog user={deletingUser} currentUserId={currentUserId}
          onClose={() => setDeletingUser(null)} onConfirm={handleDeleteUser} />
      )}
    </main>
  );
}

function StatCard({ title, value, className }: { title: string; value: number; className: string }) {
  return (
    <div className={`rounded-2xl border border-(--border-color) bg-(--surface) p-4 shadow-sm sm:p-5 ${className}`}>
      <p className="text-xs text-(--text-secondary) sm:text-sm">{title}</p>
      <p className="mt-1 text-2xl font-bold sm:text-3xl">{value}</p>
    </div>
  );
}

function FormField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block space-y-1.5">
      <span className="text-xs font-medium text-(--text-primary) sm:text-sm">{label}</span>
      {children}
    </label>
  );
}