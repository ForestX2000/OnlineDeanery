import {  useNavigate, useLocation } from "react-router-dom";
import { BookOpen, Mail, Lock, ArrowRight, ArrowLeft, CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { useAppStore, UserRole } from "@/store/useAppStore";
import { forgotPasswordRequest, loginRequest } from "../../api";


interface LocationState {
  from?: {
    pathname: string;
  };
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [isEmailSent, setIsEmailSent] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  const navigate = useNavigate();
  const location = useLocation();
  const login = useAppStore((state) => state.login);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pending) return;
    setError(null);
    setPending(true);
    try {
      const result = await loginRequest(email, password);
      login({
        email: result.user.email,
        firstName: result.user.firstName,
        lastName: result.user.lastName,
        role: (result.user.role === "admin" ? "admin" : "student") as UserRole,
      });
      const state = location.state as LocationState | null;
      const from = state?.from?.pathname || "/upload";
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось войти. Попробуйте ещё раз.");
    } finally {
      setPending(false);
    }
  };
  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (pending) return;
    setError(null);
    setPending(true);
    try {
      await forgotPasswordRequest(forgotEmail);
      setIsEmailSent(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Не удалось отправить письмо. Попробуйте ещё раз.");
    } finally {
      setPending(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#f4f7f4] flex items-center justify-center px-5 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
          <div className="inline-flex items-center justify-center rounded-2xl bg-[#087b45] p-4 text-white mb-4">
            <BookOpen size={32} />
          </div>
          <h1 className="text-3xl font-bold text-[#1e293b]">Онлайн-деканат</h1>
          <p className="mt-2 text-[#1e293b]/70">Цифровой помощник студента</p>
        </div>

        <div className="rounded-3xl border border-[#1e293b]/10 bg-white p-8 shadow-sm">
          
          {showForgotPassword ? (
            isEmailSent ? (
              <div className="text-center space-y-4 py-4">
                <div className="inline-flex items-center justify-center rounded-full bg-[#087b45]/10 p-3 text-[#087b45]">
                  <CheckCircle2 size={32} />
                </div>
                <h2 className="text-2xl font-bold text-[#1e293b]">Письмо отправлено</h2>
                <p className="text-[#1e293b]/70">
                  Мы отправили инструкцию по восстановлению пароля на адрес <br/>
                  <span className="font-semibold text-[#1e293b]">{forgotEmail}</span>
                </p>
                <button
                  onClick={() => {
                    setShowForgotPassword(false);
                    setIsEmailSent(false);
                    setForgotEmail("");
                  }}
                  className="mt-4 inline-flex items-center gap-2 text-sm font-semibold text-[#087b45] hover:text-[#065c34] transition"
                >
                  <ArrowLeft size={16} />
                  Вернуться ко входу
                </button>
              </div>
            ) : (
              <div>
                <button
                  onClick={() => setShowForgotPassword(false)}
                  className="mb-4 inline-flex items-center gap-2 text-sm font-medium text-[#1e293b]/60 hover:text-[#1e293b] transition"
                >
                  <ArrowLeft size={16} />
                  Назад ко входу
                </button>
                <h2 className="text-2xl font-bold text-[#1e293b] mb-2">Восстановление пароля</h2>
                <p className="text-sm text-[#1e293b]/70 mb-6">
                  Введите email, указанный при регистрации. Мы отправим вам ссылку для сброса пароля.
                </p>

                <form onSubmit={handleForgotPassword} className="space-y-5">
                  <div>
                    <label htmlFor="forgot-email" className="block text-sm font-medium text-[#1e293b] mb-2">
                      Email
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[#1e293b]/40" />
                      <input
                        id="forgot-email"
                        type="email"
                        value={forgotEmail}
                        onChange={(e) => setForgotEmail(e.target.value)}
                        placeholder="student@university.ru"
                        required
                        className="w-full rounded-xl border border-[#1e293b]/20 bg-white py-3 pl-11 pr-4 text-[#1e293b] placeholder:text-[#1e293b]/40 focus:border-[#087b45] focus:outline-none focus:ring-2 focus:ring-[#087b45]/20 transition"
                      />
                    </div>
                  </div>

                  <button
                    type="submit"
                    disabled={pending}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#087b45] px-6 py-3 font-semibold text-white transition hover:bg-[#065c34] disabled:opacity-60"
                  >
                    {pending ? "Отправляем..." : "Отправить ссылку"}
                    <ArrowRight size={18} />
                  </button>
                </form>
                {error && (
                  <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>
                )}
              </div>
            )
          ) : (
            <div>
              <h2 className="text-2xl font-bold text-[#1e293b] mb-6">Вход в аккаунт</h2>

              <form onSubmit={handleLogin} className="space-y-5">
                <div>
                  <label htmlFor="email" className="block text-sm font-medium text-[#1e293b] mb-2">
                    Email
                  </label>
                  <div className="relative">
                    <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[#1e293b]/40" />
                    <input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="student@university.ru"
                      required
                      className="w-full rounded-xl border border-[#1e293b]/20 bg-white py-3 pl-11 pr-4 text-[#1e293b] placeholder:text-[#1e293b]/40 focus:border-[#087b45] focus:outline-none focus:ring-2 focus:ring-[#087b45]/20 transition"
                    />
                  </div>
                </div>

                <div>
                  <label htmlFor="password" className="block text-sm font-medium text-[#1e293b] mb-2">
                    Пароль
                  </label>
                  <div className="relative">
                    <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-[#1e293b]/40" />
                    <input
                      id="password"
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="w-full rounded-xl border border-[#1e293b]/20 bg-white py-3 pl-11 pr-4 text-[#1e293b] placeholder:text-[#1e293b]/40 focus:border-[#087b45] focus:outline-none focus:ring-2 focus:ring-[#087b45]/20 transition"
                    />
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <label className="flex items-center gap-2 cursor-pointer">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-[#1e293b]/20 text-[#087b45] focus:ring-[#087b45]/20"
                    />
                    <span className="text-sm text-[#1e293b]/70">Запомнить меня</span>
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowForgotPassword(true)}
                    className="text-sm font-medium text-[#087b45] hover:text-[#065c34] transition"
                  >
                    Забыли пароль?
                  </button>
                </div>

                <button
                  type="submit"
                  disabled={pending}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#087b45] px-6 py-3 font-semibold text-white transition hover:bg-[#065c34] disabled:opacity-60"
                >
                  {pending ? "Входим..." : "Войти"}
                  <ArrowRight size={18} />
                </button>
              </form>

              {error && (
                <p role="alert" className="mt-4 text-sm text-red-700">{error}</p>
              )}

              
            </div>
          )}
        </div>

        
      </div>
    </main>
  );
}