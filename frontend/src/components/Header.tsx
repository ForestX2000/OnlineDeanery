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

  const initials = user
    ? `${user.firstName[0]}${user.lastName[0]}`.toUpperCase()
    : "";
  const isAdmin = user?.role === "admin";

  const handleLogout = () => {
    if (authToken) void logoutRequest(authToken).catch(() => undefined);
    logout();
    navigate("/login");
  };

  const hideHeaderPaths = ["/login"];
  if (hideHeaderPaths.includes(location.pathname)) return null;

  return (
    <header className="border-b border-[#1e293b]/10 bg-white px-6 py-4">
      <div className="mx-auto flex max-w-6xl items-center justify-between">
        <Link to="/" className="flex items-center gap-3">
          <div className="rounded-xl bg-[#087b45] p-2.5 text-white">
            <BookOpen size={22} />
          </div>
          <div>
            <h1 className="text-lg font-bold text-[#1e293b]">Онлайн-деканат</h1>
            <p className="text-xs text-[#1e293b]/60">
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
                className="flex items-center gap-3 rounded-xl border border-[#1e293b]/10 bg-[#f4f7f4] px-4 py-2 transition hover:bg-[#087b45]/10 hover:border-[#087b45]/30"
              >
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-[#087b45] text-sm font-bold text-white">
                  {initials}
                </div>
                <div className="hidden text-left sm:block">
                  <p className="text-sm font-semibold text-[#1e293b]">
                    {user.lastName} {user.firstName[0]}.
                  </p>
                  <p className="text-xs text-[#1e293b]/60 capitalize">
                    {isAdmin ? "Администратор" : "Студент"}
                  </p>
                </div>
              </Link>

              <button
                onClick={handleLogout}
                className="rounded-xl p-2.5 text-[#1e293b]/60 transition hover:bg-red-50 hover:text-red-600"
                title="Выйти"
              >
                <LogOut size={20} />
              </button>
            </>
          ) : (
            <Link
              to="/login"
              className="flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-medium text-[#1e293b]/70 transition hover:bg-[#f4f7f4] hover:text-[#1e293b]"
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