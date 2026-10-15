import { useNavigate, useLocation } from "react-router-dom";
import { BookOpen, Mail, Lock, ArrowRight } from "lucide-react";
import { useState, type FormEvent } from "react";
import { useAppStore, type UserRole } from "@/store/useAppStore";
import ThemeToggle from "../components/ThemeToggle";
import { loginRequest } from "../../api";

interface LocationState {
  from?: {
    pathname: string;
  };
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const navigate = useNavigate();
  const location = useLocation();
  const login = useAppStore((state) => state.login);

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault();
    if (pending) return;
    
    setError(null);
    setPending(true);
    
    try {
      const result = await loginRequest(email, password);
      
      // Сохраняем пользователя и токен в Zustand (они автоматически сохранятся в localStorage)
      login({
        email: result.user.email,
        firstName: result.user.firstName,
        lastName: result.user.lastName,
        role: (result.user.role === "admin" ? "admin" : "student") as UserRole,
      }, result.token);
      
      // Перенаправляем туда, откуда пользователь пришел, или на страницу загрузки по умолчанию
      const state = location.state as LocationState | null;
      const from = state?.from?.pathname || "/upload";
      navigate(from, { replace: true });
      
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось войти. Проверьте email и пароль.");
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="relative min-h-screen bg-[var(--app-bg)] flex items-center justify-center px-5 py-10 transition-colors duration-200">
      <ThemeToggle className="absolute right-4 top-4 sm:right-6 sm:top-6" />
      
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center justify-center rounded-2xl bg-[var(--accent)] p-4 text-white mb-4 shadow-lg shadow-[var(--accent)]/20">
            <BookOpen size={32} />
          </div>
          <h1 className="text-3xl font-bold text-[var(--text-primary)]">Онлайн-деканат</h1>
          <p className="mt-2 text-[var(--text-secondary)]">Цифровой помощник студента</p>
        </div>

        <div className="rounded-3xl border border-[var(--border-color)] bg-[var(--surface)] p-8 shadow-sm">
          <div>
            <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-6">Вход в аккаунт</h2>

            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label htmlFor="email" className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--text-secondary)]" />
                  <input
                    id="email"
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="student@university.ru"
                    required
                    className="w-full rounded-xl border border-[var(--border-color)] bg-[var(--surface)] py-3 pl-11 pr-4 text-[var(--text-primary)] placeholder:text-[var(--text-secondary)] focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/20 transition dark:bg-[var(--surface-muted)]"
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="block text-sm font-medium text-[var(--text-primary)] mb-2">
                  Пароль
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[var(--text-secondary)]" />
                  <input
                    id="password"
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    required
                    className="w-full rounded-xl border border-[var(--border-color)] bg-[var(--surface)] py-3 pl-11 pr-4 text-[var(--text-primary)] placeholder:text-[var(--text-secondary)] focus:border-[var(--accent)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)]/20 transition dark:bg-[var(--surface-muted)]"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={pending}
                className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[var(--accent)] px-6 py-3 font-semibold text-white transition hover:bg-[var(--accent-hover)] disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {pending ? "Входим..." : "Войти"}
                {!pending && <ArrowRight size={18} />}
              </button>
            </form>

            {error && (
              <p role="alert" className="mt-4 text-sm text-red-700 bg-red-50 p-3 rounded-lg border border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800">
                {error}
              </p>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}