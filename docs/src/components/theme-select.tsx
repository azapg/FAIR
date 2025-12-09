import * as React from "react"
import { Moon, Sun } from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"

export function ModeToggle() {
  const [theme, setThemeState] = React.useState<
    "light" | "dark" | "system"
  >(() => {
    if (typeof window === "undefined") return "light"
    try {
      const stored = localStorage.getItem("starlight-theme")
      if (stored === "dark" || stored === "system" || stored === "light") {
        return stored as "light" | "dark" | "system"
      }
    } catch (e) {
      // ignore localStorage errors
    }
    const dataTheme = document.documentElement.getAttribute("data-theme")
    return dataTheme === "dark" ? "dark" : "light"
  })

  React.useEffect(() => {
    const mql = window.matchMedia("(prefers-color-scheme: dark)")

    const applyTheme = (isDark: boolean) => {
      document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light")
    }

    // persist selection to localStorage
    try {
      localStorage.setItem("starlight-theme", theme)
    } catch (e) {
      // ignore localStorage errors (e.g., private mode)
    }

    if (theme === "system") {
      // apply current system preference
      applyTheme(mql.matches)

      // listen for system changes
      const handleChange = (e: MediaQueryListEvent) => applyTheme(e.matches)
      if (typeof mql.addEventListener === "function") {
        mql.addEventListener("change", handleChange)
        return () => mql.removeEventListener("change", handleChange)
      } else {
        // Safari and older browsers
        // @ts-ignore - legacy API
        mql.addListener(handleChange)
        return () => {
          // @ts-ignore - legacy API
          mql.removeListener(handleChange)
        }
      }
    } else {
      const isDark = theme === "dark"
      applyTheme(isDark)
    }
  }, [theme])

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="outline" size="icon">
          <Sun className="h-[1.2rem] w-[1.2rem] scale-100 rotate-0 transition-all dark:scale-0 dark:-rotate-90" />
          <Moon className="absolute h-[1.2rem] w-[1.2rem] scale-0 rotate-90 transition-all dark:scale-100 dark:rotate-0" />
          <span className="sr-only">Toggle theme</span>
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => setThemeState("light")}>
          Light
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setThemeState("dark")}>
          Dark
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => setThemeState("system")}>
          System
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
