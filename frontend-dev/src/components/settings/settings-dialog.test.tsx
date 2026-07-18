import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key === "settings.title" ? "Settings" : "Manage application settings.",
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
    expect(screen.getByRole("dialog", { name: "Settings" })).toBeInTheDocument()
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
