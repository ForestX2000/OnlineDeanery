import { useState, type FormEvent } from "react";
import { UserPlus, LoaderCircle, AlertCircle, CheckCircle2 } from "lucide-react";
import { CreatedUser, createUser } from "../../../api";
import { UserRole } from "@/store/useAppStore";


interface CreateUserFormProps {
  token: string;
  onUserCreated?: (user: CreatedUser) => void;
}

export default function CreateUserForm({ token, onUserCreated }: CreateUserFormProps) {
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState<UserRole>("student");
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState<CreatedUser | null>(null);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess(null);
    setIsCreating(true);

    try {
      const createdUser = await createUser(
        {
          username: username.trim(),
          email: email.trim(),
          password,
          role,
        },
        token
      );

      setSuccess(createdUser);
      onUserCreated?.(createdUser);

      // Сбрасываем форму
      setUsername("");
      setEmail("");
      setPassword("");
      setRole("student");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось создать пользователя");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
      <div className="mb-5 flex items-center gap-3">
        <div className="rounded-xl bg-indigo-100 p-2 text-indigo-700">
          <UserPlus className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-slate-900">
            Создать пользователя
          </h2>
          <p className="mt-1 text-sm text-slate-500">
            Добавление студента или администратора в систему
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-2">
          <FormField label="Имя пользователя">
            <input
              required
              minLength={2}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Например, ivan_ivanov"
              autoComplete="username"
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </FormField>

          <FormField label="Электронная почта">
            <input
              required
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
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
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Не менее 8 символов"
              autoComplete="new-password"
              className="w-full rounded-lg border border-slate-300 px-3 py-2.5 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            />
          </FormField>

          <FormField label="Роль">
            <select
              value={role}
              onChange={(e) => setRole(e.target.value as UserRole)}
              className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 outline-none focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100"
            >
              <option value="student">Студент</option>
              <option value="admin">Администратор</option>
            </select>
          </FormField>
        </div>

        {error && (
          <div
            role="alert"
            className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        {success && (
          <div
            role="status"
            className="flex items-start gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800"
          >
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
            <div>
              <p className="font-semibold">Пользователь создан</p>
              <p className="mt-1">
                {success.username} — {success.email}
              </p>
              <p className="mt-1">
                Роль: {success.role}. ID: {success.user_id}
              </p>
            </div>
          </div>
        )}

        <button
          type="submit"
          disabled={isCreating}
          className="inline-flex items-center justify-center gap-2 rounded-lg bg-indigo-600 px-5 py-2.5 font-medium text-white transition hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isCreating ? (
            <LoaderCircle className="h-4 w-4 animate-spin" />
          ) : (
            <UserPlus className="h-4 w-4" />
          )}
          {isCreating ? "Создание..." : "Создать пользователя"}
        </button>
      </form>
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