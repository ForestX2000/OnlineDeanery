import { BookOpen } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-[#1e293b]/10 bg-white px-6 py-8">
      <div className="mx-auto max-w-6xl">
        <div className="flex flex-col items-center justify-between gap-4 sm:flex-row">
          <div className="flex items-center gap-3">
            <div className="rounded-lg bg-[#087b45] p-2 text-white">
              <BookOpen size={18} />
            </div>
            <div>
              <p className="text-sm font-semibold text-[#1e293b]">Онлайн-деканат</p>
              <p className="text-xs text-[#1e293b]/60">Цифровой помощник студента</p>
            </div>
          </div>

          <div className="flex items-center gap-6 text-sm text-[#1e293b]/60">
            <a href="#" className="hover:text-[#087b45] transition">О сервисе</a>
            <a href="#" className="hover:text-[#087b45] transition">Помощь</a>
            <a href="#" className="hover:text-[#087b45] transition">Контакты</a>
          </div>
        </div>

        <div className="mt-6 border-t border-[#1e293b]/10 pt-6 text-center text-xs text-[#1e293b]/50">
          © 2026 Онлайн-деканат. Все права защищены.
        </div>
      </div>
    </footer>
  );
}