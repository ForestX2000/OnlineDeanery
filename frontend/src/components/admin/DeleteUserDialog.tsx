import { useState } from "react";
import { AlertTriangle, LoaderCircle, X } from "lucide-react";
import { AdminUser } from "api";


interface DeleteUserDialogProps {
  user: AdminUser;
  currentUserId?: number;
  onClose: () => void;
  onConfirm: (userId: number) => Promise<void>;
}

export default function DeleteUserDialog({ user, currentUserId, onClose, onConfirm }: DeleteUserDialogProps) {
  const [isDeleting, setIsDeleting] = useState(false);
  const [error, setError] = useState("");
  const isSelf = currentUserId === user.user_id;

  const handleDelete = async () => {
    if (isSelf) {
      setError("Вы не можете удалить свой собственный аккаунт.");
      return;
    }
    setIsDeleting(true);
    setError("");
    try {
      await onConfirm(user.user_id);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось удалить пользователя");
      setIsDeleting(false);
    }
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
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
            Удаление пользователя
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

        <div 
          className="mb-5 flex items-start gap-3 rounded-xl border p-4"
          style={{
            backgroundColor: '#fee2e2',
            borderColor: '#fecaca'
          }}
        >
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" style={{ color: '#dc2626' }} />
          <div>
            <p className="font-semibold" style={{ color: '#991b1b' }}>Вы уверены?</p>
            <p className="mt-1 text-sm" style={{ color: '#b91c1c' }}>
              Пользователь <span className="font-semibold">{user.username}</span> ({user.email}) будет{" "}
              <span className="font-semibold">безвозвратно удалён</span>. Это действие нельзя отменить.
            </p>
          </div>
        </div>

        {error && (
          <div 
            className="mb-4 flex items-start gap-2 rounded-lg border p-3 text-sm"
            style={{
              backgroundColor: '#fee2e2',
              borderColor: '#fecaca',
              color: '#b91c1c'
            }}
          >
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="button" 
            onClick={onClose} 
            disabled={isDeleting}
            className="flex-1 rounded-lg border px-4 py-2.5 font-medium transition disabled:opacity-60"
            style={{
              backgroundColor: 'var(--surface)',
              borderColor: 'var(--border-color)',
              color: 'var(--text-primary)'
            }}
            onMouseEnter={(e) => {
              if (!isDeleting) e.currentTarget.style.backgroundColor = 'var(--surface-muted)';
            }}
            onMouseLeave={(e) => {
              if (!isDeleting) e.currentTarget.style.backgroundColor = 'var(--surface)';
            }}
          >
            Отмена
          </button>
          <button
            type="button" 
            onClick={handleDelete} 
            disabled={isDeleting || isSelf}
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2.5 font-medium text-white transition disabled:cursor-not-allowed disabled:opacity-60"
            style={{
              backgroundColor: '#dc2626'
            }}
            onMouseEnter={(e) => {
              if (!isDeleting && !isSelf) e.currentTarget.style.backgroundColor = '#b91c1c';
            }}
            onMouseLeave={(e) => {
              if (!isDeleting && !isSelf) e.currentTarget.style.backgroundColor = '#dc2626';
            }}
          >
            {isDeleting ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
            {isDeleting ? "Удаление..." : "Удалить"}
          </button>
        </div>
      </div>
    </div>
  );
}