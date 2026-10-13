import { Moon, Sun } from "lucide-react";
import { useTheme } from "next-themes";

export default function ThemeToggle({ className = "" }: { className?: string }) {
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === "dark";
  const label = isDark ? "Включить светлую тему" : "Включить тёмную тему";

  return (
    <button
      type="button"
      onClick={() => setTheme(isDark ? "light" : "dark")}
      className={`rounded-xl p-2.5 text-[#1e293b]/70 transition hover:bg-[#f4f7f4] hover:text-[#087b45] ${className}`}
      title={label}
      aria-label={label}
    >
      {isDark ? <Sun size={20} /> : <Moon size={20} />}
    </button>
  );
}
