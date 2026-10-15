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
    <header className="border-b border-[var(--border-color)] bg-[var(--surface)] px-6 py-4">
      <div className="mx-auto flex max-w-6xl items-center justify-between">
        <Link to="/" className="flex items-center gap-3">
          <div className="rounded-xl bg-[var(--accent)] p-2.5 text-white">
            <BookOpen size={22} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-[var(--text-primary)]">Онлайн-деканат</h1>
            <p className="text-xs text-[var(--text-secondary)]">
              {isAdmin
                ? "Панель администратора"
                : user
                  ? "Цифровой помощник студента"
                  : "Цифровой помощник студента"}
            </p>
          </div>
        </Link>

        <div className="flex items-center gap-2 sm:gap-3">
          <ThemeToggle />
          {isAuthenticated && user ? (
            <>
              <Link
                to="/profile"
                className="flex items-center gap-3 rounded-xl border border-[var(--border-color)] bg-[var(--surface-muted)] px-4 py-2 transition hover:bg-[var(--accent)]/10 hover:border-[var(--accent)]/30"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[var(--accent)] text-sm font-bold text-white">
                  {initials || "?"}
                </div>
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
                className="rounded-xl p-2.5 text-[var(--text-secondary)] transition hover:bg-rose-50 hover:text-rose-600 dark:hover:bg-rose-900/30"
                title="Выйти"
              >
                <LogOut size={20} />
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-(--text-secondary) transition hover:bg-(--surface-muted) hover:text-(--text-primary)"
            >
              <LogIn size={18} />
              Войти
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}