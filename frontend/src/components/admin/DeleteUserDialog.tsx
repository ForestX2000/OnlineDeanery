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
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#1e293b]/50 p-4" onClick={onClose}>
      <div className="w-full max-w-md rounded-2xl bg-[#ffffff] p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <div className="mb-5 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-[#1e293b]">Удаление пользователя</h2>
          <button onClick={onClose} className="rounded-lg p-1.5 text-[#64748b] transition hover:bg-[#f8faf9] hover:text-[#1e293b]">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mb-5 flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-rose-600" />
          <div>
            <p className="font-semibold text-rose-900">Вы уверены?</p>
            <p className="mt-1 text-sm text-rose-700">
              Пользователь <span className="font-semibold">{user.username}</span> ({user.email}) будет{" "}
              <span className="font-semibold">безвозвратно удалён</span>. Это действие нельзя отменить.
            </p>
          </div>
        </div>

        {error && (
          <div className="mb-4 flex items-start gap-2 rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{error}</span>
          </div>
        )}

        <div className="flex gap-3">
          <button
            type="button" onClick={onClose} disabled={isDeleting}
            className="flex-1 rounded-lg border border-[#e2e8f0] bg-[#ffffff] px-4 py-2.5 font-medium text-[#1e293b] transition hover:bg-[#f8faf9] disabled:opacity-60"
          >
            Отмена
          </button>
          <button
            type="button" onClick={handleDelete} disabled={isDeleting || isSelf}
            className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-rose-600 px-4 py-2.5 font-medium text-white transition hover:bg-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isDeleting ? <LoaderCircle className="h-4 w-4 animate-spin" /> : null}
            {isDeleting ? "Удаление..." : "Удалить"}
          </button>
        </div>
      </div>
    </div>
  );
}