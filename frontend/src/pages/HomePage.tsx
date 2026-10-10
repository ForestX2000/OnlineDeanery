import { Link } from "react-router-dom";
import { ArrowRight, FileText, BookOpen, ShieldCheck } from "lucide-react";

export default function HomePage() {
  return (
    <div className="min-h-screen bg-[#f4f7f4] text-[#1e293b]">
      <header className="border-b border-[#1e293b]/10 bg-white">
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-6 py-5">
          <div className="rounded-xl bg-[#087b45] p-3 text-white">
            <BookOpen size={24} />
          </div>
          <div>
            <h1 className="text-lg font-bold">Онлайн-деканат</h1>
            <p className="text-sm text-[#1e293b]/60">
              Цифровой помощник студента
            </p>
          </div>
        </div>
      </header>

      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-20 md:grid-cols-2 md:py-28">
          <div>
            <p className="mb-5 inline-block rounded-full bg-[#087b45]/10 px-4 py-2 text-sm font-medium text-[#087b45]">
              Помощь студентам
            </p>

            <h2 className="text-4xl font-extrabold leading-tight sm:text-5xl">
              Университетские документы —
              <span className="block text-[#087b45]">
                теперь понятнее
              </span>
            </h2>

            <p className="mt-6 max-w-lg text-lg leading-8 text-[#1e293b]/70">
              Загрузи документ, задай вопрос и получи ответ
              с опорой на нормативные документы университета.
            </p>

            <Link
              to="/upload"
              className="mt-8 inline-flex items-center gap-3 rounded-xl bg-[#087b45] px-6 py-4 font-semibold text-white transition hover:bg-[#065c34]"
            >
              Загрузить документ
              <ArrowRight size={20} />
            </Link>
          </div>

          <div className="rounded-3xl border border-[#1e293b]/10 bg-white p-8 shadow-xl shadow-[#1e293b]/5">
            <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-[#087b45]/10 text-[#087b45]">
              <FileText size={32} />
            </div>

            <h3 className="text-2xl font-bold">
              Разберёмся вместе
            </h3>

            <p className="mt-3 leading-7 text-[#1e293b]/70">
              Не знаешь, что означает пункт в справке или
              какие правила применяются к твоей ситуации?
              Начни с загрузки документа.
            </p>

            <div className="mt-7 space-y-4">
              <div className="flex items-start gap-3">
                <ShieldCheck className="mt-1 text-[#087b45]" />
                <div>
                  <p className="font-semibold">Ответы с подтверждениями</p>
                  <p className="text-sm text-[#1e293b]/60">
                    Источники и цитаты, когда они доступны
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <BookOpen className="mt-1 text-[#087b45]" />
                <div>
                  <p className="font-semibold">Простым языком</p>
                  <p className="text-sm text-[#1e293b]/60">
                    Помощь в понимании документов
                  </p>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="border-t border-[#1e293b]/10 bg-white px-6 py-14">
          <div className="mx-auto max-w-6xl text-center">
            <h3 className="text-2xl font-bold">Как это работает</h3>
            <div className="mt-8 grid gap-6 text-left md:grid-cols-3">
              {[
                ["01", "Загрузи документ", "Выбери файл и укажи его тип."],
                ["02", "Задай вопрос", "Напиши, что именно хочешь узнать."],
                ["03", "Изучи ответ", "Посмотри результат и подтверждающие источники."],
              ].map(([number, title, description]) => (
                <div key={number} className="rounded-2xl border border-[#1e293b]/10 bg-[#f4f7f4] p-6">
                  <p className="font-bold text-[#087b45]">{number}</p>
                  <h4 className="mt-3 text-lg font-bold">{title}</h4>
                  <p className="mt-2 text-[#1e293b]/70">{description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </main>

      <footer className="px-6 py-8 text-center text-sm text-[#1e293b]/60">
        Онлайн-деканат · Цифровой помощник студента
      </footer>
    </div>
  );
}
