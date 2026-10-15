import { Link, useNavigate, useLocation } from "react-router-dom";
import { BookOpen, LogOut, LogIn } from "lucide-react";
import { logoutRequest } from "../../api";
import { useAppStore } from "@/store/useAppStore";
import ThemeToggle from "./ThemeToggle";

export default function Header() {
  const user = useAppStore((state) => state.user);
  const authToken = useAppStore((state) => state.authToken);
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const logout = useAppStore((state) => state.logout);
  const navigate = useNavigate();
  const location = useLocation();

  const getInitials = () => {
    if (!user) return "";
    const first = user.firstName?.[0]?.toUpperCase() || "";
    const last = user.lastName?.[0]?.toUpperCase() || "";
    return first + last;
  };

  const initials = getInitials();
  const isAdmin = user?.role === "admin";

  const handleLogout = () => {
    if (authToken) void logoutRequest(authToken).catch(() => undefined);
    logout();
    navigate("/login");
  };

  const hideHeaderPaths = ["/login"];
  if (hideHeaderPaths.includes(location.pathname)) return null;

  return (
    <header className="border-b border-[var(--border-color)] bg-[var(--surface)] px-3 py-3 sm:px-6 sm:py-4">
      <div className="mx-auto flex max-w-6xl items-center justify-between">
        {/* Логотип */}
        <Link to="/" className="flex items-center gap-2 sm:gap-3 min-w-0">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-[var(--accent)] text-white shrink-0 sm:h-11 sm:w-11">
            <BookOpen size={20} className="sm:size-[22px]" />
          </div>
          <div className="min-w-0">
            <h1 className="text-base font-bold text-[var(--text-primary)] truncate sm:text-lg">
              Онлайн-деканат
            </h1>
            {/* Скрываем подзаголовок на мобильных */}
            <p className="hidden text-xs text-[var(--text-secondary)] sm:block">
              {isAdmin ? "Панель администратора" : "Цифровой помощник студента"}
            </p>
          </div>
        </Link>

        {/* Правая часть */}
        <div className="flex items-center gap-1.5 sm:gap-3">
          <ThemeToggle />
          {isAuthenticated && user ? (
            <>
              <Link
                to="/profile"
                className="flex items-center gap-2 rounded-xl border border-[var(--border-color)] bg-[var(--surface-muted)] px-2 py-1.5 transition hover:bg-[var(--accent)]/10 hover:border-[var(--accent)]/30 sm:px-4 sm:py-2"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[var(--accent)] text-xs font-bold text-white sm:h-9 sm:w-9 sm:text-sm">
                  {initials || "?"}
                </div>
                {/* Имя показываем только на sm+ */}
                <div className="hidden text-left sm:block">
                  <p className="text-sm font-semibold text-[var(--text-primary)]">
                    {user.lastName || user.firstName || user.email}
                  </p>
                  <p className="text-xs text-[var(--text-secondary)] capitalize">
                    {isAdmin ? "Администратор" : "Студент"}
                  </p>
                </div>
              </Link>

              <button
                onClick={handleLogout}
                className="rounded-xl p-2 text-[var(--text-secondary)] transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-900/30 sm:p-2.5"
                title="Выйти"
              >
                <LogOut size={18} className="sm:size-[20px]" />
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium text-[var(--text-secondary)] transition hover:bg-[var(--surface-muted)] hover:text-[var(--text-primary)] sm:px-4"
            >
              <LogIn size={16} className="sm:size-[18px]" />
              <span className="hidden sm:inline">Войти</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}