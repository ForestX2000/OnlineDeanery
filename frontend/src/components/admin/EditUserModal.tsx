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
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4 dark:bg-black/70" 
      onClick={onClose}
      style={{ backgroundColor: 'rgba(0, 0, 0, 0.5)' }}
    >
      <div 
        className="w-full max-w-md rounded-2xl p-6 shadow-xl"
        onClick={(e) => e.stopPropagation()}
        style={{
          backgroundColor: 'var(--surface)',
          color: 'var(--text-primary)'
        }}
      >
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-xl font-semibold" style={{ color: 'var(--text-primary)' }}>
            Редактирование пользователя
          </h2>
          <button 
            onClick={onClose} 
            className="rounded-lg p-1.5 transition"
            style={{ color: 'var(--text-secondary)' }}
            onMouseEnter={(e) => {
              e.currentTarget.style.backgroundColor = 'var(--surface-muted)';
              e.currentTarget.style.color = 'var(--text-primary)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.backgroundColor = 'transparent';
              e.currentTarget.style.color = 'var(--text-secondary)';
            }}
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {isSelf && (
          <div 
            className="mb-4 flex items-start gap-2 rounded-lg border p-3 text-sm"
            style={{
              borderColor: 'var(--accent)',
              backgroundColor: 'var(--accent)',
              opacity: 0.1,
              color: 'var(--accent)'
            }}
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>Вы редактируете свой аккаунт. Роль нельзя изменить на "Студент".</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)' }}>
              Имя пользователя
            </label>
            <input
              required 
              minLength={2} 
              value={username} 
              onChange={(e) => setUsername(e.target.value)}
              className="w-full rounded-lg border px-3 py-2.5 outline-none transition"
              style={{
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)'
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent)';
                e.currentTarget.style.boxShadow = '0 0 0 2px var(--accent)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-color)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)' }}>
              Email
            </label>
            <input
              required 
              type="email" 
              value={email} 
              onChange={(e) => setEmail(e.target.value)}
              className="w-full rounded-lg border px-3 py-2.5 outline-none transition"
              style={{
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)'
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent)';
                e.currentTarget.style.boxShadow = '0 0 0 2px var(--accent)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-color)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            />
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)' }}>
              Роль
            </label>
            <select
              value={role} 
              onChange={(e) => setRole(e.target.value as "student" | "admin")} 
              disabled={isSelf}
              className="w-full rounded-lg border px-3 py-2.5 outline-none transition"
              style={{
                backgroundColor: isSelf ? 'var(--surface-muted)' : 'var(--surface)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)',
                cursor: isSelf ? 'not-allowed' : 'pointer'
              }}
              onFocus={(e) => {
                if (!isSelf) {
                  e.currentTarget.style.borderColor = 'var(--accent)';
                  e.currentTarget.style.boxShadow = '0 0 0 2px var(--accent)';
                }
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-color)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            >
              <option value="student">Студент</option>
              <option value="admin">Администратор</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium mb-1.5" style={{ color: 'var(--text-primary)' }}>
              Новый пароль 
              <span className="font-normal" style={{ color: 'var(--text-secondary)' }}>
                (оставьте пустым, чтобы не менять)
              </span>
            </label>
            <input
              type="password" 
              minLength={8} 
              value={password} 
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Не менее 8 символов" 
              autoComplete="new-password"
              className="w-full rounded-lg border px-3 py-2.5 outline-none transition"
              style={{
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)'
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent)';
                e.currentTarget.style.boxShadow = '0 0 0 2px var(--accent)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = 'var(--border-color)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            />
          </div>

          {error && (
            <div 
              className="flex items-start gap-2 rounded-lg border p-3 text-sm"
              style={{
                backgroundColor: '#fee2e2',
                borderColor: '#fecaca',
                color: '#b91c1c'
              }}
            >
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="flex gap-3 pt-2">
            <button
              type="button" 
              onClick={onClose}
              className="flex-1 rounded-lg border px-4 py-2.5 font-medium transition"
              style={{
                backgroundColor: 'var(--surface)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)'
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--surface-muted)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.backgroundColor = 'var(--surface)';
              }}
            >
              Отмена
            </button>
            <button
              type="submit" 
              disabled={isSaving}
              className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 font-medium text-white transition disabled:cursor-not-allowed disabled:opacity-60"
              style={{
                backgroundColor: isSaving ? 'var(--accent)' : 'var(--accent)'
              }}
              onMouseEnter={(e) => {
                if (!isSaving) e.currentTarget.style.backgroundColor = 'var(--accent-hover)';
              }}
              onMouseLeave={(e) => {
                if (!isSaving) e.currentTarget.style.backgroundColor = 'var(--accent)';
              }}
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