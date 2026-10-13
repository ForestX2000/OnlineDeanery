import { Link } from "react-router-dom";
import {
  ArrowRight, FileText, BookOpen, ShieldCheck,
  Bell, Calendar, ChevronRight, UploadCloud
} from "lucide-react";
import { useAppStore } from "@/store/useAppStore";


const UNIVERSITY_NEWS = [
  {
    id: 1,
    title: "Изменения в расписании зимней сессии",
    date: "10 октября 2026",
    category: "Учебный процесс",
    description: "Обратите внимание на новые даты проведения экзаменов для 3 и 4 курсов факультета компьютерных наук.",
  },
  {
    id: 2,
    title: "Приём заявок на повышенную стипендию",
    date: "08 октября 2026",
    category: "Финансы",
    description: "Открыт сбор документов для назначения повышенной государственной академической стипендии за научную деятельность.",
  },
  {
    id: 3,
    title: "День открытых дверей факультета ИТ",
    date: "05 октября 2026",
    category: "Мероприятия",
    description: "Приглашаем всех желающих познакомиться с новыми образовательными программами и лабораториями.",
  },
];

export default function HomePage() {
  const { isAuthenticated, user } = useAppStore();


  if (isAuthenticated && user) {
    return (
      <div className="min-h-screen bg-[#f4f7f4]">
        <main className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">
          <div className="mb-6 rounded-3xl bg-[#087b45] p-6 text-white shadow-lg sm:mb-10 sm:p-8 md:p-10">
            <h2 className="text-2xl font-bold sm:text-3xl md:text-4xl">
              Добро пожаловать, {user.firstName}!
            </h2>
            <p className="mt-3 max-w-xl text-base text-white/80 sm:text-lg">
              Чем мы можем помочь вам сегодня? Загрузите документ для мгновенного анализа или ознакомьтесь с последними новостями.
            </p>
            <Link
              to="/upload"
              className="mt-6 inline-flex w-full items-center justify-center gap-3 rounded-xl bg-white px-6 py-4 font-semibold text-[#087b45] transition hover:bg-[#f4f7f4] sm:mt-8 sm:w-auto"
            >
              <UploadCloud size={20} />
              Загрузить новый документ
            </Link>
          </div>

          <div>
            <div className="mb-4 flex flex-col gap-3 sm:mb-6 sm:flex-row sm:items-center sm:justify-between">
              <h3 className="flex items-center gap-2 text-xl font-bold text-[#1e293b] sm:text-2xl">
                <Bell className="text-[#087b45]" size={24} />
                Новости университета
              </h3>
              <button className="flex items-center gap-1 self-start text-sm font-medium text-[#087b45] hover:text-[#065c34] transition sm:self-auto">
                Все новости <ChevronRight size={16} />
              </button>
            </div>

            <div className="grid gap-4 sm:grid-cols-2 sm:gap-6 lg:grid-cols-3">
              {UNIVERSITY_NEWS.map((news) => (
                <div
                  key={news.id}
                  className="group rounded-2xl border border-[#1e293b]/10 bg-white p-5 shadow-sm transition hover:border-[#087b45]/30 hover:shadow-md sm:p-6"
                >
                  <div className="mb-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                    <span className="inline-flex w-fit rounded-full bg-[#087b45]/10 px-2 py-0.5 text-xs font-semibold text-[#087b45] sm:px-3 sm:py-1">
                      {news.category}
                    </span>
                    <span className="flex items-center gap-1 text-xs text-[#1e293b]/50 whitespace-nowrap">
                      <Calendar size={14} className="shrink-0" />
                      <span>{news.date}</span>
                    </span>
                  </div>
                  <h4 className="text-base font-bold text-[#1e293b] group-hover:text-[#087b45] transition sm:text-lg">
                    {news.title}
                  </h4>
                  <p className="mt-3 text-sm leading-6 text-[#1e293b]/70">
                    {news.description}
                  </p>
                  <button className="mt-5 flex items-center gap-2 text-sm font-semibold text-[#087b45] opacity-0 transition group-hover:opacity-100">
                    Читать далее <ArrowRight size={16} />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>
    );
  }


  return (
    <div className="min-h-screen bg-[#f4f7f4] text-[#1e293b]">
      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-8 px-4 py-12 sm:px-6 sm:py-16 md:gap-12 md:py-20 lg:py-28">
          <div className="md:col-span-1">
            <p className="mb-4 inline-block rounded-full bg-[#087b45]/10 px-4 py-2 text-xs font-medium text-[#087b45] sm:text-sm">
              Помощь студентам
            </p>

            <h2 className="text-3xl font-extrabold leading-tight sm:text-4xl md:text-5xl">
              Университетские документы —
              <span className="block text-[#087b45]">
                теперь понятнее
              </span>
            </h2>

            <p className="mt-5 max-w-lg text-base leading-7 text-[#1e293b]/70 sm:mt-6 sm:text-lg sm:leading-8">
              Загрузи документ, задай вопрос и получи ответ
              с опорой на нормативные документы университета.
            </p>

            <Link
              to="/login"
              className="mt-6 inline-flex w-full items-center justify-center gap-3 rounded-xl bg-[#087b45] px-6 py-4 font-semibold text-white transition hover:bg-[#065c34] sm:mt-8 sm:w-auto"
            >
              Войти в систему
              <ArrowRight size={20} />
            </Link>
          </div>

          <div className="rounded-3xl border border-[#1e293b]/10 bg-white p-6 shadow-xl shadow-[#1e293b]/5 sm:p-8">
            <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#087b45]/10 text-[#087b45] sm:h-16 sm:w-16">
              <FileText size={28} className="sm:hidden" />
              <FileText size={32} className="hidden sm:block" />
            </div>

            <h3 className="text-xl font-bold sm:text-2xl">
              Разберёмся вместе
            </h3>

            <p className="mt-3 text-sm leading-6 text-[#1e293b]/70 sm:text-base sm:leading-7">
              Не знаешь, что означает пункт в справке или
              какие правила применяются к твоей ситуации?
              Начни с загрузки документа.
            </p>

            <div className="mt-6 space-y-4 sm:mt-7">
              <div className="flex items-start gap-3">
                <ShieldCheck className="mt-1 text-[#087b45]" size={20} />
                <div>
                  <p className="font-semibold">Ответы с подтверждениями</p>
                  <p className="text-sm text-[#1e293b]/60">
                    Источники и цитаты, когда они доступны
                  </p>
                </div>
              </div>

              <div className="flex items-start gap-3">
                <BookOpen className="mt-1 text-[#087b45]" size={20} />
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

        <section className="border-t border-[#1e293b]/10 bg-white px-4 py-10 sm:px-6 sm:py-14">
          <div className="mx-auto max-w-6xl text-center">
            <h3 className="text-xl font-bold sm:text-2xl">Как это работает</h3>
            <div className="mt-6 grid gap-4 text-left sm:mt-8 sm:gap-6 md:grid-cols-3">
              {[
                ["01", "Загрузи документ", "Выбери файл и укажи его тип."],
                ["02", "Задай вопрос", "Напиши, что именно хочешь узнать."],
                ["03", "Изучи ответ", "Посмотри результат и подтверждающие источники."],
              ].map(([number, title, description]) => (
                <div key={number} className="rounded-2xl border border-[#1e293b]/10 bg-[#f4f7f4] p-5 sm:p-6">
                  <p className="font-bold text-[#087b45]">{number}</p>
                  <h4 className="mt-3 text-base font-bold sm:text-lg">{title}</h4>
                  <p className="mt-2 text-sm text-[#1e293b]/70 sm:text-base">{description}</p>
                </div>
              ))}
            </div>
          </div>
        </section>

      </main>
    </div>
  );
}
