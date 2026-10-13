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
      className={`inline-flex h-10 w-10 items-center justify-center rounded-xl border border-slate-200 bg-white text-slate-700 transition-all duration-300 hover:bg-slate-100 dark:border-yellow-400/30 dark:bg-slate-800 dark:text-yellow-300 dark:shadow-[0_0_12px_rgba(250,204,21,0.2)] dark:hover:bg-slate-700 dark:hover:text-yellow-200 dark:hover:shadow-[0_0_18px_rgba(250,204,21,0.5)] ${className}`}
      title={label}
      aria-label={label}
    >
      {isDark ? (
        <Sun
          size={22}
          strokeWidth={2.5}
          className="drop-shadow-[0_0_5px_rgba(250,204,21,0.8)]"
        />
      ) : (
        <Moon size={20} />
      )}
    </button>
  );
}
