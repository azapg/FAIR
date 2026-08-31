import { cleanup, fireEvent, render, renderHook, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) => key === "submissions.feedbackPlaceholder" ? "Add feedback" : key,
    i18n: { language: "en" },
  }),
}))

import { useSubmissionColumns } from "./submissions"

afterEach(cleanup)

describe("submission feedback accessibility", () => {
  it("uses a native button for editable feedback", () => {
    const onFeedbackClick = vi.fn()
    const submission = { id: "submission-1", draftFeedback: null }
    const { result } = renderHook(() => useSubmissionColumns(true))
    const feedbackColumn = result.current.find(
      (column) => "accessorKey" in column && column.accessorKey === "draftFeedback",
    )

    expect(feedbackColumn).toBeDefined()
    const cell = feedbackColumn?.cell
    expect(typeof cell).toBe("function")
    if (typeof cell !== "function") return

    render(cell({
      getValue: () => "",
      row: { original: submission },
      table: { options: { meta: { onFeedbackClick } } },
    } as never))

    fireEvent.click(screen.getByRole("button", { name: "Add feedback" }))
    expect(onFeedbackClick).toHaveBeenCalledWith(submission)
  })
})
