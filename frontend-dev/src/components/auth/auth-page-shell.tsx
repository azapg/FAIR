import { ReactNode } from "react";

import { LanguageSwitcher } from "@/components/language-switcher";
import { ThemeToggle } from "@/components/theme-toggle";

export function AuthPageShell({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-background">
      <main className="flex min-h-[calc(100vh-64px)] items-center justify-center p-6">
        <div className="w-full max-w-md rounded-xl p-6">
          {children}
        </div>
      </main>
      <footer className="px-4 py-3 text-end">
        <LanguageSwitcher />
        <ThemeToggle />
      </footer>
    </div>
  );
}
