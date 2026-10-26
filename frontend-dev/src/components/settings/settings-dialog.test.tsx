import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => ({
      "settings.title": "Settings",
      "settings.description": "Manage application settings.",
      "settings.navigationLabel": "Settings sections",
      "settings.close": "Close settings",
    })[key] ?? key,
  }),
}))

vi.mock("@/components/settings/settings-sections", () => ({
  SETTINGS_CATEGORY_ORDER: [],
  SETTINGS_SECTIONS: [],
}))

import { SettingsDialog } from "./settings-dialog"
import { CommandDialog } from "@/components/ui/command"

afterEach(cleanup)

describe("accessible dialogs", () => {
  it("names the desktop settings dialog", () => {
    render(<SettingsDialog open onOpenChange={vi.fn()} isMobile={false} />)
    const dialog = screen.getByRole("dialog", { name: "Settings" })

    expect(dialog).toBeInTheDocument()
    expect(dialog).toHaveClass("h-[90vh]")
    expect(dialog).toHaveClass("!max-w-[1200px]")
    expect(dialog).not.toHaveClass("!inset-0")

    const closeButton = screen.getByRole("button", { name: "Close settings" })
    expect(closeButton).toHaveClass("absolute", "top-4", "right-4", "size-10", "rounded-full")
  })

  it("names command dialogs", () => {
    render(
      <CommandDialog open title="Search FAIR" description="Search navigation.">
        <div>Commands</div>
      </CommandDialog>,
    )
    expect(screen.getByRole("dialog", { name: "Search FAIR" })).toBeInTheDocument()
  })
})
