<<<<<<< Updated upstream
import {  useNavigate, useLocation } from "react-router-dom";
import { BookOpen, Mail, Lock, ArrowRight, ArrowLeft, CheckCircle2 } from "lucide-react";
import { useState } from "react";
import { useAppStore, UserRole } from "@/store/useAppStore";

=======
import { useNavigate, useLocation } from "react-router-dom";
import { BookOpen, Mail, Lock, ArrowRight, ArrowLeft, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { useState } from "react";
import { useAppStore } from "@/store/useAppStore";
import { loginUser, forgotPassword, ApiError } from "@api";
>>>>>>> Stashed changes

interface LocationState {
  from?: {
    pathname: string;
  };
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
<<<<<<< Updated upstream
  
  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [isEmailSent, setIsEmailSent] = useState(false);
=======
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [showForgotPassword, setShowForgotPassword] = useState(false);
  const [forgotEmail, setForgotEmail] = useState("");
  const [isEmailSent, setIsEmailSent] = useState(false);
  const [forgotLoading, setForgotLoading] = useState(false);
  const [forgotError, setForgotError] = useState<string | null>(null);
>>>>>>> Stashed changes

  const navigate = useNavigate();
  const location = useLocation();
  const login = useAppStore((state) => state.login);

<<<<<<< Updated upstream
  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault();
    
    
    const isAdmin = email.toLowerCase().includes("admin");
    
    
    const mockUser = {
      email,
      firstName: isAdmin ? "Алексей" : "Иван",
      lastName: isAdmin ? "Админов" : "Студентов",
      role: (isAdmin ? "admin" : "student") as UserRole, // <-- Исправление здесь
    };

    login(mockUser);
    
    const state = location.state as LocationState | null;
    const from = state?.from?.pathname || "/upload";
    navigate(from, { replace: true });
  };
  const handleForgotPassword = (e: React.FormEvent) => {
    e.preventDefault();
    console.log("Forgot password request for:", forgotEmail);
    setIsEmailSent(true);
=======
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await loginUser(email, password);
      
      login({
        email: response.user.email,
        firstName: response.user.firstName,
        lastName: response.user.lastName,
        role: response.user.role as "student" | "admin",
      });

      const state = location.state as LocationState | null;
      const from = state?.from?.pathname || "/upload";
      navigate(from, { replace: true });
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else if (err instanceof Error) {
        setError(err.message);
      } else {
        setError("Произошла ошибка при входе. Попробуйте еще раз.");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setForgotLoading(true);
    setForgotError(null);

    try {
      await forgotPassword(forgotEmail);
      setIsEmailSent(true);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        setForgotError(err.message);
      } else if (err instanceof Error) {
        setForgotError(err.message);
      } else {
        setForgotError("Не удалось отправить запрос на восстановление.");
      }
    } finally {
      setForgotLoading(false);
    }
>>>>>>> Stashed changes
  };

  return (
    <main className="min-h-screen bg-[#f4f7f4] flex items-center justify-center px-5 py-10">
      <div className="w-full max-w-md">
        <div className="mb-8 text-center">
<<<<<<< Updated upstream
          <div className="inline-flex items-center justify-center rounded-2xl bg-[#087b45] p-4 text-white mb-4">
=======
          <div className="inline-flex items-center justify-center rounded-2xl bg-[#087b45] p-4 text-white mb-4 shadow-sm">
>>>>>>> Stashed changes
            <BookOpen size={32} />
          </div>
          <h1 className="text-3xl font-bold text-[#1e293b]">Онлайн-деканат</h1>
          <p className="mt-2 text-[#1e293b]/70">Цифровой помощник студента</p>
        </div>

        <div className="rounded-3xl border border-[#1e293b]/10 bg-white p-8 shadow-sm">
<<<<<<< Updated upstream
          
=======
>>>>>>> Stashed changes
          {showForgotPassword ? (
            isEmailSent ? (
              <div className="text-center space-y-4 py-4">
                <div className="inline-flex items-center justify-center rounded-full bg-[#087b45]/10 p-3 text-[#087b45]">
                  <CheckCircle2 size={32} />
                </div>
                <h2 className="text-2xl font-bold text-[#1e293b]">Письмо отправлено</h2>
<<<<<<< Updated upstream
                <p className="text-[#1e293b]/70">
                  Мы отправили инструкцию по восстановлению пароля на адрес <br/>
                  <span className="font-semibold text-[#1e293b]">{forgotEmail}</span>
=======
                <p className="text-sm text-[#1e293b]/70 leading-relaxed">
                  Мы отправили инструкции по восстановлению пароля на адрес <br />
                  <span className="font-semibold text-[#1e293b]">{forgotEmail}</span>. <br />
                  Пожалуйста, проверьте ваш почтовый ящик.
>>>>>>> Stashed changes
                </p>
                <button
                  onClick={() => {
                    setShowForgotPassword(false);
                    setIsEmailSent(false);
                    setForgotEmail("");
<<<<<<< Updated upstream
=======
                    setForgotError(null);
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
                  onClick={() => setShowForgotPassword(false)}
=======
                  onClick={() => {
                    setShowForgotPassword(false);
                    setForgotError(null);
                  }}
>>>>>>> Stashed changes
                  className="mb-4 inline-flex items-center gap-2 text-sm font-medium text-[#1e293b]/60 hover:text-[#1e293b] transition"
                >
                  <ArrowLeft size={16} />
                  Назад ко входу
                </button>
                <h2 className="text-2xl font-bold text-[#1e293b] mb-2">Восстановление пароля</h2>
<<<<<<< Updated upstream
                <p className="text-sm text-[#1e293b]/70 mb-6">
                  Введите email, указанный при регистрации. Мы отправим вам ссылку для сброса пароля.
                </p>

=======
                <p className="text-sm text-[#1e293b]/70 mb-6 leading-relaxed">
                  Введите email, указанный при регистрации. Мы отправим вам новый пароль для входа.
                </p>

                {forgotError && (
                  <div className="mb-5 flex items-start gap-2.5 rounded-xl bg-red-50 p-3.5 text-sm text-red-700 border border-red-200">
                    <AlertCircle size={18} className="shrink-0 mt-0.5" />
                    <span>{forgotError}</span>
                  </div>
                )}

>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
                    className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#087b45] px-6 py-3 font-semibold text-white transition hover:bg-[#065c34]"
                  >
                    Отправить ссылку
                    <ArrowRight size={18} />
=======
                    disabled={forgotLoading}
                    className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#087b45] px-6 py-3 font-semibold text-white transition hover:bg-[#065c34] disabled:opacity-50"
                  >
                    {forgotLoading ? (
                      <>
                        <Loader2 size={18} className="animate-spin" />
                        Отправка...
                      </>
                    ) : (
                      <>
                        Отправить ссылку
                        <ArrowRight size={18} />
                      </>
                    )}
>>>>>>> Stashed changes
                  </button>
                </form>
              </div>
            )
          ) : (
            <div>
              <h2 className="text-2xl font-bold text-[#1e293b] mb-6">Вход в аккаунт</h2>

<<<<<<< Updated upstream
=======
              {error && (
                <div className="mb-5 flex items-start gap-2.5 rounded-xl bg-red-50 p-3.5 text-sm text-red-700 border border-red-200">
                  <AlertCircle size={18} className="shrink-0 mt-0.5" />
                  <span>{error}</span>
                </div>
              )}

>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
                    onClick={() => setShowForgotPassword(true)}
=======
                    onClick={() => {
                      setShowForgotPassword(true);
                      setError(null);
                    }}
>>>>>>> Stashed changes
                    className="text-sm font-medium text-[#087b45] hover:text-[#065c34] transition"
                  >
                    Забыли пароль?
                  </button>
                </div>

                <button
                  type="submit"
<<<<<<< Updated upstream
                  className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#087b45] px-6 py-3 font-semibold text-white transition hover:bg-[#065c34]"
                >
                  Войти
                  <ArrowRight size={18} />
                </button>
              </form>

              
            </div>
          )}
        </div>

        
=======
                  disabled={loading}
                  className="w-full inline-flex items-center justify-center gap-2 rounded-xl bg-[#087b45] px-6 py-3 font-semibold text-white transition hover:bg-[#065c34] disabled:opacity-50"
                >
                  {loading ? (
                    <>
                      <Loader2 size={18} className="animate-spin" />
                      Вход в систему...
                    </>
                  ) : (
                    <>
                      Войти
                      <ArrowRight size={18} />
                    </>
                  )}
                </button>
              </form>

              {/* Подсказка для тестирования */}
              <div className="mt-6 rounded-xl bg-[#f4f7f4] p-3 text-xs text-[#1e293b]/60 leading-relaxed text-center">
                Тестовые аккаунты из базы деканата: <br />
                Студент: <span className="font-semibold">student@university.ru</span> / <span className="font-semibold">123456</span> <br />
                Админ: <span className="font-semibold">admin@university.ru</span> / <span className="font-semibold">admin123</span>
              </div>
            </div>
          )}
        </div>
>>>>>>> Stashed changes
      </div>
    </main>
  );
}