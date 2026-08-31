import * as React from "react"
import { cleanup, fireEvent, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/hooks/use-courses", () => ({
  useCourses: () => ({ data: [] }),
}))

import { ChatCanvas } from "./chat-canvas"
import { ChatInput } from "./chat-input"
import { ElicitationPanel } from "./elicitation-panel"
import { SourcesSidebar } from "./sources-sidebar"

afterEach(cleanup)

describe("chat accessibility", () => {
  it("gives the composer stable accessible names", () => {
    const onSend = vi.fn()
    render(<ChatInput onSend={onSend} />)

    const input = screen.getByRole("textbox", { name: "Message" })
    expect(screen.getByRole("button", { name: "Add attachments or tools" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Dictate message" })).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Start voice conversation" })).toBeInTheDocument()

    fireEvent.change(input, { target: { value: "Hello" } })
    fireEvent.click(screen.getByRole("button", { name: "Send message" }))

    expect(onSend).toHaveBeenCalledWith("Hello", [])
  })

  it("moves focus to a blocking elicitation and restores it when dismissed", () => {
    function Harness() {
      const [open, setOpen] = React.useState(false)
      return (
        <>
          <button type="button" onClick={() => setOpen(true)}>Open question</button>
          {open && (
            <ElicitationPanel
              elicitation={{
                id: "interaction-1",
                questions: [
                  {
                    id: "question-1",
                    title: "Choose one",
                    options: [{ label: "Continue", value: "continue" }],
                  },
                ],
              }}
              onResolve={vi.fn()}
              onDismiss={() => setOpen(false)}
            />
          )}
        </>
      )
    }

    render(<Harness />)
    const opener = screen.getByRole("button", { name: "Open question" })
    opener.focus()
    fireEvent.click(opener)

    expect(screen.getByRole("heading", { name: "Choose one" })).toHaveFocus()
    expect(screen.getByRole("textbox", { name: "Custom response" })).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Dismiss question" }))
    expect(opener).toHaveFocus()
  })

  it("names transient side panels and restores focus after closing them", () => {
    function Harness() {
      const [panel, setPanel] = React.useState<"canvas" | "sources" | null>(null)
      return (
        <>
          <button type="button" onClick={() => setPanel("canvas")}>Open canvas</button>
          <button type="button" onClick={() => setPanel("sources")}>Open sources</button>
          {panel === "canvas" && (
            <ChatCanvas
              activeCanvasContent={{ title: "Result", type: "Code", visualType: "code", code: "42" }}
              setCanvaOpen={() => setPanel(null)}
            />
          )}
          {panel === "sources" && (
            <SourcesSidebar
              sources={[{ index: 1, title: "Reference", url: "https://example.com" }]}
              onClose={() => setPanel(null)}
            />
          )}
        </>
      )
    }

    render(<Harness />)
    const canvasOpener = screen.getByRole("button", { name: "Open canvas" })
    canvasOpener.focus()
    fireEvent.click(canvasOpener)
    expect(screen.getByRole("complementary", { name: "Result" })).toBeInTheDocument()
    const closeCanvas = screen.getByRole("button", { name: "Close canvas" })
    expect(closeCanvas).toHaveFocus()
    fireEvent.click(closeCanvas)
    expect(canvasOpener).toHaveFocus()

    const sourcesOpener = screen.getByRole("button", { name: "Open sources" })
    sourcesOpener.focus()
    fireEvent.click(sourcesOpener)
    expect(screen.getByRole("complementary", { name: "Sources" })).toBeInTheDocument()
    expect(screen.getByRole("link", { name: "Open Reference in a new tab" })).toBeInTheDocument()
    const closeSources = screen.getByRole("button", { name: "Close sources" })
    expect(closeSources).toHaveFocus()
    fireEvent.click(closeSources)
    expect(sourcesOpener).toHaveFocus()
  })
})
