import * as React from "react"
import { Moon, Sun, Check } from "lucide-react"
import { useTranslation } from "react-i18next"
import { usePreferenceSettings } from "@/hooks/use-preference-settings"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export function ThemeToggle() {
  const { setThemePreference, effectiveTheme } = usePreferenceSettings()
  const { t } = useTranslation()

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          <Sun className="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
          <Moon className="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
          <span className="sr-only">{t('theme.toggleTheme')}</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setThemePreference("light")}>
          <span>{t('theme.light')}</span>
          <Check className={`ml-auto h-4 w-4 ${effectiveTheme === "light" ? "opacity-100" : "opacity-0"}`} />
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setThemePreference("dark")}>
          <span>{t('theme.dark')}</span>
          <Check className={`ml-auto h-4 w-4 ${effectiveTheme === "dark" ? "opacity-100" : "opacity-0"}`} />
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setThemePreference("system")}>
          <span>{t('theme.system')}</span>
          <Check className={`ml-auto h-4 w-4 ${effectiveTheme === "system" ? "opacity-100" : "opacity-0"}`} />
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
