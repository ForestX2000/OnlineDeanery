import { Link, useNavigate, useLocation } from "react-router-dom";
import { BookOpen, LogOut, LogIn, Moon, Sun } from "lucide-react";
import { useAppStore } from "@/store/useAppStore";
import { useTheme } from "@/context/useTheme";

export default function Header() {
  const user = useAppStore((state) => state.user);
  const isAuthenticated = useAppStore((state) => state.isAuthenticated);
  const logout = useAppStore((state) => state.logout);

  const { theme, toggleTheme } = useTheme();

  const navigate = useNavigate();
  const location = useLocation();

  const initials = user
    ? `${user.firstName[0]}${user.lastName[0]}`.toUpperCase()
    : "";

  const isAdmin = user?.role === "admin";

  const handleLogout = () => {
    logout();
    navigate("/login");
  };

  const hideHeaderPaths = ["/login"];

  if (hideHeaderPaths.includes(location.pathname)) {
    return null;
  }

  return (
    <header className="border-b border-[#1e293b]/10 bg-white px-4 py-4 transition-colors dark:border-slate-700 dark:bg-slate-900 sm:px-6">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-3">
        <Link to="/" className="flex min-w-0 items-center gap-3">
          <div className="shrink-0 rounded-xl bg-[#087b45] p-2.5 text-white">
            <BookOpen size={22} />
          </div>

          <div className="min-w-0">
            <h1 className="text-lg font-bold text-[#1e293b] dark:text-white">
              Онлайн-деканат
            </h1>

            <p className="text-xs text-[#1e293b]/60 dark:text-slate-400">
              {isAdmin ? "Панель администратора" : "Цифровой помощник студента"}
            </p>
          </div>
        </Link>

        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          {/* Переключение темы */}
          <button
            type="button"
            onClick={toggleTheme}
            aria-label={
              theme === "dark"
                ? "Включить светлую тему"
                : "Включить тёмную тему"
            }
            title={theme === "dark" ? "Светлая тема" : "Тёмная тема"}
            className="inline-flex h-10 w-10 items-center justify-center rounded-xl
    border border-slate-200 bg-white text-slate-700
    transition-all duration-300 hover:bg-slate-100
    dark:border-yellow-400/30 dark:bg-slate-800
    dark:text-yellow-300 dark:shadow-[0_0_12px_rgba(250,204,21,0.2)]
    dark:hover:bg-slate-700 dark:hover:text-yellow-200
    dark:hover:shadow-[0_0_18px_rgba(250,204,21,0.5)]"
          >
            {theme === "dark" ? (
              <Sun
                size={22}
                strokeWidth={2.5}
                className="drop-shadow-[0_0_5px_rgba(250,204,21,0.8)]"
              />
            ) : (
              <Moon size={20} />
            )}
          </button>

          {isAuthenticated && user ? (
            <>
              <Link
                to="/profile"
                className="flex items-center gap-3 rounded-xl border border-[#1e293b]/10 bg-[#f4f7f4] px-2 py-2 transition hover:border-[#087b45]/30 hover:bg-[#087b45]/10 dark:border-slate-700 dark:bg-slate-800 dark:hover:bg-slate-700 sm:px-4"
              >
                <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-[#087b45] text-sm font-bold text-white">
                  {initials}
                </div>

                <div className="hidden text-left sm:block">
                  <p className="text-sm font-semibold text-[#1e293b] dark:text-white">
                    {user.lastName} {user.firstName[0]}.
                  </p>

                  <p className="text-xs capitalize text-[#1e293b]/60 dark:text-slate-400">
                    {isAdmin ? "Администратор" : "Студент"}
                  </p>
                </div>
              </Link>

              <button
                type="button"
                onClick={handleLogout}
                className="rounded-xl p-2.5 text-[#1e293b]/60 transition hover:bg-red-50 hover:text-red-600 dark:text-slate-400 dark:hover:bg-red-950 dark:hover:text-red-400"
                title="Выйти"
                aria-label="Выйти из аккаунта"
              >
                <LogOut size={20} />
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm font-medium text-[#1e293b]/70 transition hover:bg-[#f4f7f4] hover:text-[#1e293b] dark:text-slate-300 dark:hover:bg-slate-800 dark:hover:text-white sm:px-4"
            >
              <LogIn size={18} />
              <span>Войти</span>
            </Link>
          )}
        </div>
      </div>
    </header>
  );
}
