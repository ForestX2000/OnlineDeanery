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

// Используем относительные пути, так как они гарантированно работают в вашей структуре
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
  if (error instanceof Error) {
    return error.message;
  }
  return "Произошла непредвиденная ошибка.";
}

function formatDate(date: string): string {
  const parsedDate = new Date(date);
  if (Number.isNaN(parsedDate.getTime())) {
    return date;
  }
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

  // Список пользователей (для админа)
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [usersLoading, setUsersLoading] = useState(true);
  const [usersError, setUsersError] = useState("");

  // Модалки редактирования и удаления
  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [deletingUser, setDeletingUser] = useState<AdminUser | null>(null);

  // Форма создания пользователя
  const [username, setUsername] = useState("");
  const [newEmail, setNewEmail] = useState("");
  const [password, setPassword] = useState("");
  const [newRole, setNewRole] = useState<UserRole>("student");
  const [creatingUser, setCreatingUser] = useState(false);
  const [createError, setCreateError] = useState("");
  const [createSuccess, setCreateSuccess] = useState<CreatedUser | null>(null);

  const isAdmin = user?.role === "admin";


  // 👉 ДОБАВЬТЕ ЭТИ ДВЕ СТРОКИ:
  // Находим email текущего пользователя и исключаем его из списка для отображения
  const currentUserEmail = user?.email;
  const visibleUsers = users.filter((u) => u.email !== currentUserEmail);

  // ID текущего пользователя всё ещё нужен для передачи в модалки (на всякий случай)
  const currentUserId = users.find(
    (u) => u.email === currentUserEmail,
  )?.user_id;

  const displayName =
    [user?.firstName, user?.lastName].filter(Boolean).join(" ") ||
    user?.email ||
    "Пользователь";




  const sessionExpired = user !== null && token === null;
  const visibleError = error ?? (sessionExpired ? "Сессия истекла. Войдите в аккаунт, чтобы открыть историю." : null);

  useEffect(() => {
    if (!user) {
      navigate("/login", { replace: true });
    }
  }, [user, navigate]);

  useEffect(() => {
    if (!user || !token) return;
    const authToken = token;
    let cancelled = false;

    async function loadHistory() {
      try {
        const result = await getRequestHistory(authToken);
        if (!cancelled) {
          setHistory(result);
          setError("");
        }
      } catch (err) {
        if (!cancelled) setError(getErrorMessage(err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    void loadHistory();
    return () => {
      cancelled = true;
    };
  }, [user, token]);

  useEffect(() => {
    let cancelled = false;
    async function loadDocumentTypes() {
      try {
        const result = await getDocumentTypes();
        if (!cancelled) setDocumentTypes(result);
      } catch {
        // История останется доступной
      }
    }
    void loadDocumentTypes();
    return () => {
      cancelled = true;
    };
  }, []);

  // Загрузка списка пользователей для админа
  useEffect(() => {
    if (!isAdmin || !token) return;
    const authToken = token;
    let cancelled = false;

    async function loadUsers() {
      try {
        setUsersLoading(true);
        const result = await getUsers(authToken);
        if (!cancelled) {
          setUsers(result);
          setUsersError("");
        }
      } catch (err) {
        if (!cancelled) setUsersError(getErrorMessage(err));
      } finally {
        if (!cancelled) setUsersLoading(false);
      }
    }

    void loadUsers();
    return () => {
      cancelled = true;
    };
  }, [isAdmin, token]);

  const filteredHistory = useMemo(() => {
    const normalizedSearch = search.trim().toLowerCase();
    return history.filter((item) => {
      const matchesStatus =
        statusFilter === "all" || item.status === statusFilter;
      const matchesCategory =
        categoryFilter === "all" || item.document_type === categoryFilter;
      const searchableText = [
        item.question,
        item.answer,
        item.document_type,
        item.user_name,
        item.user_email,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      const matchesSearch =
        !normalizedSearch || searchableText.includes(normalizedSearch);
      return matchesStatus && matchesCategory && matchesSearch;
    });
  }, [history, search, statusFilter, categoryFilter]);

  const stats = useMemo(() => {
    const resolved = history.filter(
      (item) => item.status === "resolved",
    ).length;
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
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            username: username.trim(),
            email: newEmail.trim(),
            password,
            role: newRole,
          }),
        },
      );

      const responseText = await response.text();
      let responseData: unknown = null;
      if (responseText) {
        try {
          responseData = JSON.parse(responseText);
        } catch {
          responseData = responseText;
        }
      }

      if (!response.ok) {
        const message =
          typeof responseData === "object" &&
          responseData !== null &&
          "detail" in responseData
            ? String(responseData.detail)
            : typeof responseData === "string" && responseData
              ? responseData
              : `Не удалось создать пользователя (${response.status}).`;
        throw new Error(message);
      }

      const createdUser = responseData as CreatedUser;
      setCreateSuccess(createdUser);

      // Добавляем нового пользователя в таблицу без перезагрузки
      setUsers((prev) => [
        ...prev,
        {
          user_id: createdUser.user_id,
          username: createdUser.username,
          email: createdUser.email,
          role: createdUser.role,
          created_at: createdUser.created_at,
        },
      ]);

      setUsername("");
      setNewEmail("");
      setPassword("");
      setNewRole("student");
    } catch (err) {
      setCreateError(getErrorMessage(err));
    } finally {
      setCreatingUser(false);
    }
  }

  // 👉 НОВЫЕ ФУНКЦИИ: Обновление и удаление
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
        <div className="flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 p-4 text-amber-800">
          <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
          <div>
            <h2 className="font-semibold">Требуется авторизация</h2>
            <p className="mt-1 text-sm">
              Сессия отсутствует или истекла. Войдите в аккаунт.
            </p>
            <button
              type="button"
              onClick={() => navigate("/login")}
              className="mt-3 rounded-lg bg-amber-700 px-4 py-2 text-sm font-medium text-white hover:bg-amber-800"
            >
              Перейти ко входу
            </button>
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-6xl space-y-8 px-4 py-8 sm:px-6 lg:px-8">
      {/* Заголовок профиля */}
      <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-100 text-indigo-700">
              <ShieldCheck className="h-7 w-7" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">
                Личный кабинет
              </h1>
              <p className="mt-1 text-slate-600">{displayName}</p>
              <p className="mt-1 flex items-center gap-2 text-sm text-slate-500">
                <Mail className="h-4 w-4" />
                {user.email}
              </p>
            </div>
          </div>
          <span className="inline-flex w-fit items-center rounded-full bg-indigo-50 px-3 py-1.5 text-sm font-medium text-indigo-700">
            {isAdmin ? "Администратор" : "Студент"}
          </span>
        </div>
      </section>

      {/* Статистика (только для админа) */}
      {isAdmin && (
        <section>
          <h2 className="mb-4 text-xl font-semibold text-slate-900">
            Статистика запросов
          </h2>
          <div className="grid gap-4 sm:grid-cols-3">
            <StatCard
              title="Всего запросов"
              value={stats.total}
              className="bg-indigo-50 text-indigo-700"
            />
            <StatCard
              title="Успешных"
              value={stats.resolved}
              className="bg-emerald-50 text-emerald-700"
            />
            <StatCard
              title="С ошибками"
              value={stats.failed}
              className="bg-rose-50 text-rose-700"
            />
          </div>
        </section>
      )}

      {/* Управление пользователями (только для админа) */}
      {isAdmin && (
        <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-xl bg-indigo-100 p-2 text-indigo-700">
              <UserPlus className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-xl font-semibold text-slate-900">
                Управление пользователями
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Добавление, редактирование и удаление пользователей
              </p>
            </div>
          </div>

          <form onSubmit={handleCreateUser} className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <FormField label="Имя пользователя">
                <input
                  required
                  minLength={2}
                  value={username}
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="Например, ivan_ivanov"
                  autoComplete="username"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                />
              </FormField>

              <FormField label="Электронная почта">
                <input
                  required
                  type="email"
                  value={newEmail}
                  onChange={(event) => setNewEmail(event.target.value)}
                  placeholder="student@example.com"
                  autoComplete="email"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                />
              </FormField>

              <FormField label="Пароль">
                <input
                  required
                  minLength={8}
                  type="password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Не менее 8 символов"
                  autoComplete="new-password"
                  className="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                />
              </FormField>

              <FormField label="Роль">
                <select
                  value={newRole}
                  onChange={(event) =>
                    setNewRole(event.target.value as UserRole)
                  }
                  className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
                >
                  <option value="student">Студент</option>
                  <option value="admin">Администратор</option>
                </select>
              </FormField>
            </div>

            {createError && (
              <div
                role="alert"
                className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700"
              >
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>{createError}</span>
              </div>
            )}

            {createSuccess && (
              <div
                role="status"
                className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800"
              >
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
                <div>
                  <p className="font-semibold">Пользователь создан</p>
                  <p className="mt-1">
                    {createSuccess.username} — {createSuccess.email}
                  </p>
                  <p className="mt-1">
                    Роль: {createSuccess.role}. ID: {createSuccess.user_id}
                  </p>
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={creatingUser}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {creatingUser ? (
                <LoaderCircle className="h-4 w-4 animate-spin" />
              ) : (
                <UserPlus className="h-4 w-4" />
              )}
              {creatingUser ? "Создание..." : "Создать пользователя"}
            </button>
          </form>

          {/* Таблица пользователей */}
          <div className="mt-8 border-t border-slate-200 pt-6">
            <h3 className="mb-4 text-lg font-semibold text-slate-900">
              Зарегистрированные пользователи
            </h3>

            {usersLoading ? (
              <div className="flex items-center justify-center gap-2 rounded-xl border border-slate-200 bg-slate-50 p-6 text-slate-600">
                <LoaderCircle className="h-5 w-5 animate-spin" />
                Загрузка списка...
              </div>
            ) : usersError ? (
              <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                <span>Не удалось загрузить список: {usersError}</span>
              </div>
            ) : users.length === 0 ? (
              <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 text-center text-slate-500">
                Пользователи пока не созданы
              </div>
            ) : (
              <div className="overflow-hidden rounded-xl border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                        ID
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                        Имя
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                        Email
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wider text-slate-500">
                        Роль
                      </th>
                      <th className="px-4 py-3 text-right text-xs font-semibold uppercase tracking-wider text-slate-500">
                        Действия
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 bg-white">
                    {visibleUsers.map((u) => (
                      <tr
                        key={u.user_id}
                        className="hover:bg-slate-50 transition-colors"
                      >
                        <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-500">
                          #{u.user_id}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-sm font-medium text-slate-900">
                          {u.username}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-sm text-slate-600">
                          {u.email}
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-sm">
                          <span
                            className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                              u.role === "admin"
                                ? "bg-rose-100 text-rose-700"
                                : "bg-emerald-100 text-emerald-700"
                            }`}
                          >
                            {u.role === "admin" ? "Админ" : "Студент"}
                          </span>
                        </td>
                        <td className="whitespace-nowrap px-4 py-3 text-right">
                          <div className="inline-flex items-center justify-end gap-2">
                            <button
                              onClick={() => setEditingUser(u)}
                              className="rounded-lg p-2 text-slate-400 transition hover:bg-indigo-50 hover:text-indigo-600"
                              title="Редактировать"
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => setDeletingUser(u)}
                              className="rounded-lg p-2 text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
                              title="Удалить"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </section>
      )}

      {/* История запросов */}
      <section className="space-y-5">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">
              История запросов
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              Все ваши обращения и результаты обработки документов
            </p>
          </div>
          <button
            type="button"
            onClick={() => window.location.reload()}
            className="inline-flex items-center justify-center gap-2 rounded-lg border border-slate-300 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            <RefreshCw className="h-4 w-4" />
            Обновить страницу
          </button>
        </div>

        <div className="grid gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-sm sm:grid-cols-3">
          <div className="relative sm:col-span-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
            <input
              value={search}
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Поиск по запросам..."
              className="w-full rounded-lg border border-slate-300 py-2.5 pl-9 pr-3 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </div>

          <select
            value={statusFilter}
            onChange={(event) =>
              setStatusFilter(event.target.value as StatusFilter)
            }
            aria-label="Фильтр по статусу"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-indigo-500"
          >
            <option value="all">Все статусы</option>
            <option value="resolved">Успешные</option>
            <option value="failed">С ошибками</option>
          </select>

          <select
            value={categoryFilter}
            onChange={(event) => setCategoryFilter(event.target.value)}
            aria-label="Фильтр по типу документа"
            className="rounded-lg border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-indigo-500"
          >
            <option value="all">Все типы документов</option>
            {documentTypes.map((type) => (
              <option key={type.id} value={type.label}>
                {type.label}
              </option>
            ))}
          </select>
        </div>

        {loading ? (
          <div className="flex items-center justify-center gap-3 rounded-2xl border border-slate-200 bg-white p-10 text-slate-600">
            <LoaderCircle className="h-5 w-5 animate-spin" />
            Загружаем историю запросов...
          </div>
        ) : error ? (
          <div
            role="alert"
            className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-rose-700"
          >
            <AlertCircle className="mt-0.5 h-5 w-5 shrink-0" />
            <div>
              <p className="font-semibold">Не удалось загрузить историю</p>
              <p className="mt-1 text-sm">{error}</p>
            </div>
          </div>
        ) : filteredHistory.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 bg-white p-10 text-center">
            <FileText className="mx-auto h-10 w-10 text-slate-400" />
            <h3 className="mt-3 font-semibold text-slate-800">
              Запросы не найдены
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              Попробуйте изменить фильтры или выполнить новый запрос.
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredHistory.map((item) => {
              const expanded = expandedRequest === item.request_id;
              const succeeded = item.status === "resolved";
              return (
                <article
                  key={item.request_id}
                  className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
                >
                  <button
                    type="button"
                    onClick={() =>
                      setExpandedRequest(expanded ? null : item.request_id)
                    }
                    aria-expanded={expanded}
                    className="flex w-full items-center justify-between gap-4 p-4 text-left transition hover:bg-slate-50 sm:p-5"
                  >
                    <div className="flex min-w-0 items-start gap-3">
                      <div
                        className={`mt-0.5 rounded-xl p-2 ${succeeded ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700"}`}
                      >
                        {succeeded ? (
                          <CheckCircle2 className="h-5 w-5" />
                        ) : (
                          <AlertCircle className="h-5 w-5" />
                        )}
                      </div>
                      <div className="min-w-0">
                        <h3 className="font-semibold text-slate-900">
                          {item.document_type || "Запрос"}
                        </h3>
                        <p className="mt-1 line-clamp-2 text-sm text-slate-600">
                          {item.question || "Без текста запроса"}
                        </p>
                        <p className="mt-2 text-xs text-slate-500">
                          {formatDate(item.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <span
                        className={`hidden rounded-full px-2.5 py-1 text-xs font-medium sm:inline-flex ${
                          succeeded
                            ? "bg-emerald-50 text-emerald-700"
                            : "bg-rose-50 text-rose-700"
                        }`}
                      >
                        {succeeded ? "Успешно" : "Ошибка"}
                      </span>
                      <ChevronDown
                        className={`h-5 w-5 text-slate-400 transition-transform ${expanded ? "rotate-180" : ""}`}
                      />
                    </div>
                  </button>

                  {expanded && (
                    <div className="space-y-4 border-t border-slate-200 bg-slate-50 p-4 sm:p-5">
                      {isAdmin && (
                        <div className="grid gap-2 text-sm sm:grid-cols-2">
                          <p className="text-slate-600">
                            <span className="font-medium text-slate-800">
                              Пользователь:
                            </span>{" "}
                            {item.user_name || "Не указан"}
                          </p>
                          <p className="text-slate-600">
                            <span className="font-medium text-slate-800">
                              Email:
                            </span>{" "}
                            {item.user_email || "Не указан"}
                          </p>
                        </div>
                      )}
                      <div>
                        <h4 className="text-sm font-semibold text-slate-800">
                          Запрос
                        </h4>
                        <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                          {item.question || "Нет текста запроса"}
                        </p>
                      </div>
                      <div>
                        <h4 className="text-sm font-semibold text-slate-800">
                          Ответ системы
                        </h4>
                        <p className="mt-1 whitespace-pre-wrap text-sm text-slate-700">
                          {item.answer || "Ответ отсутствует"}
                        </p>
                      </div>
                      <p className="text-xs text-slate-500">
                        ID запроса: {item.request_id}
                      </p>
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}

        {!loading && !error && filteredHistory.length > 0 && (
          <p className="text-center text-sm text-slate-500">
            Показано запросов: {filteredHistory.length} из {history.length}
          </p>
        )}
      </section>

      {/* 👉 МОДАЛЬНЫЕ ОКНА (в самом конце, перед закрывающим main) */}
      {editingUser && (
        <EditUserModal
          user={editingUser}
          currentUserId={currentUserId}
          onClose={() => setEditingUser(null)}
          onSave={handleUpdateUser}
        />
      )}

      {deletingUser && (
        <DeleteUserDialog
          user={deletingUser}
          currentUserId={currentUserId}
          onClose={() => setDeletingUser(null)}
          onConfirm={handleDeleteUser}
        />
      )}
    </main>
  );
}

function StatCard({
  title,
  value,
  className,
}: {
  title: string;
  value: number;
  className: string;
}) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <p className="text-sm text-slate-500">{title}</p>
      <p
        className={`mt-2 text-3xl font-bold ${className.split(" ").pop() ?? ""}`}
      >
        {value}
      </p>
    </div>
  );
}

function FormField({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="block space-y-1.5">
      <span className="text-sm font-medium text-slate-700">{label}</span>
      {children}
    </label>
  );
}
