import { useState, type FormEvent } from "react";
import { X, LoaderCircle, AlertCircle } from "lucide-react";
import { AdminUser, UpdateUserRequest } from "api";


interface EditUserModalProps {
  user: AdminUser;
  currentUserId?: number;
  onClose: () => void;
  onSave: (userId: number, data: UpdateUserRequest) => Promise<void>;
}

export default function EditUserModal({ user, currentUserId, onClose, onSave }: EditUserModalProps) {
  const [username, setUsername] = useState(user.username);
  const [email, setEmail] = useState(user.email);
  const [role, setRole] = useState<"student" | "admin">(user.role === "admin" ? "admin" : "student");
  const [password, setPassword] = useState("");
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState("");

  const isSelf = currentUserId === user.user_id;

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");

    if (isSelf && role !== "admin") {
      setError("Вы не можете понизить свою собственную роль.");
      return;
    }

    setIsSaving(true);
    try {
      const data: UpdateUserRequest = { username: username.trim(), email: email.trim(), role };
      if (password.trim()) data.password = password.trim();
      
      await onSave(user.user_id, data);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось сохранить изменения");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#1e293b]/50 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl bg-[#ffffff] p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[#1e293b]">Редактирование пользователя</h2>
          <button onClick={onClose} className="rounded-lg p-1.5 text-[#64748b] transition hover:bg-[#f8faf9] hover:text-[#1e293b]">
            <X className="h-5 w-5" />
          </button>
        </div>

        {isSelf && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-[#087b45]/20 bg-[#087b45]/10 p-3 text-sm text-[#087b45]">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>Вы редактируете свой аккаунт. Роль нельзя изменить на "Студент".</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-[#1e293b] mb-1.5">Имя пользователя</label>
            <input
              required minLength={2} value={username} onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border border-[#e2e8f0] bg-[#ffffff] px-3 py-2.5 text-[#1e293b] outline-none transition focus:border-[#087b45] focus:ring-2 focus:ring-[#087b45]/20"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#1e293b] mb-1.5">Email</label>
            <input
              required type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border border-[#e2e8f0] bg-[#ffffff] px-3 py-2.5 text-[#1e293b] outline-none transition focus:border-[#087b45] focus:ring-2 focus:ring-[#087b45]/20"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-[#1e293b] mb-1.5">Роль</label>
            <select
              value={role} onChange={(e) => setRole(e.target.value as "student" | "admin")} disabled={isSelf}
              className="w-full rounded-lg border border-[#e2e8f0] bg-[#ffffff] px-3 py-2.5 text-[#1e293b] outline-none transition focus:border-[#087b45] focus:ring-2 focus:ring-[#087b45]/20 disabled:bg-[#f8faf9] disabled:cursor-not-allowed"
            >
              <option value="student">Студент</option>
              <option value="admin">Администратор</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-[#1e293b] mb-1.5">
              Новый пароль <span className="text-[#64748b] font-normal">(оставьте пустым, чтобы не менять)</span>
            </label>
            <input
              type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)}
              placeholder="Не менее 8 символов" autoComplete="new-password"
              className="w-full rounded-lg border border-[#e2e8f0] bg-[#ffffff] px-3 py-2.5 text-[#1e293b] outline-none transition focus:border-[#087b45] focus:ring-2 focus:ring-[#087b45]/20"
            />
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button" onClick={onClose}
              className="flex-1 rounded-lg border border-[#e2e8f0] bg-[#ffffff] px-4 py-2.5 font-medium text-[#1e293b] transition hover:bg-[#f8faf9]"
            >
              Отмена
            </button>
            <button
              type="submit" disabled={isSaving}
              className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-[#087b45] px-4 py-2.5 font-medium text-white transition hover:bg-[#075c36] disabled:cursor-not-allowed disabled:opacity-60"
            >
              {isSaving ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
              {isSaving ? "Сохранение..." : "Сохранить"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}