import { useNavigate } from "react-router-dom";
import { ArrowLeft, Home } from "lucide-react";

export default function PageNotFound() {
  const navigate = useNavigate();

  return (
    <main className="flex min-h-screen items-center justify-center bg-(--app-bg) px-4 py-12 transition-colors duration-200 sm:px-6 lg:px-8">
      <div className="w-full max-w-md text-center">
        <h1 className="text-6xl font-bold tracking-tight text-(--text-primary) sm:text-8xl">
          404
        </h1>
        <h2 className="mt-4 text-xl font-semibold text-(--text-primary) sm:text-2xl">
          Страница не найдена
        </h2>
        <p className="mt-3 text-sm leading-relaxed text-(--text-secondary) sm:text-base">
          Возможно, она была удалена, перемещена или вы ввели неверный адрес в
          адресной строке.
        </p>

        <div className="mt-8 flex flex-col gap-3 sm:flex-row sm:justify-center">
          <button
            onClick={() => navigate("/")}
            className="inline-flex items-center justify-center gap-2 rounded-xl bg-(--accent) px-6 py-3 text-sm font-semibold text-white transition hover:bg-(--accent-hover) focus:outline-none focus:ring-2 focus:ring-(--accent)/50 sm:text-base"
          >
            <Home className="h-4 w-4 sm:h-5 sm:w-5" />
            На главную
          </button>

          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center justify-center gap-2 rounded-xl border border-(--border-color) bg-(--surface) px-6 py-3 text-sm font-semibold text-(--text-primary) transition hover:bg-(--surface-muted) focus:outline-none focus:ring-2 focus:ring-(--border-color) sm:text-base"
          >
            <ArrowLeft className="h-4 w-4 sm:h-5 sm:w-5" />
            Вернуться назад
          </button>
        </div>
      </div>
    </main>
  );
}
    