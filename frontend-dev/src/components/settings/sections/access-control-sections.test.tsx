import { cleanup, render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"

const updateCapability = vi.fn()

vi.mock("react-i18next", () => ({
  useTranslation: () => ({
    t: (key: string) =>
      ({
        "settings.access.aiControls": "AI controls",
        "settings.access.aiControlsDescription": "Control AI execution credits.",
        "settings.access.enforceCredits": "Enforce credits",
        "settings.access.weightedNotCurrency": "Credits are weights, not currency.",
        "settings.access.unclassifiedWarning": "One capability is unclassified.",
        "settings.access.capabilityCosts": "Capability costs",
        "settings.access.capabilityCostsDescription": "Classify every capability.",
        "settings.access.unclassified": "Unclassified",
        "settings.access.unmetered": "Unmetered",
        "settings.access.aiMetered": "AI metered",
        "settings.access.classify": "Classify",
        "settings.access.usageAudit": "Usage audit",
        "settings.access.usageAuditDescription": "Review reservations.",
        "settings.access.currentMonthCredits": "Current month credits",
      })[key] ?? key,
  }),
}))

vi.mock("@/hooks/use-access-controls", () => ({
  usePlatformPolicy: () => ({
    data: {
      effectiveAiControlsEnabled: false,
      aiControlsLocked: false,
    },
    isLoading: false,
  }),
  useUpdatePlatformPolicy: () => ({ mutate: vi.fn(), isPending: false }),
  useCapabilityCostPolicies: () => ({
    data: [
      {
        capabilityDefinitionId: "capability-1",
        capabilityId: "agent.chat",
        displayName: "Agent",
        version: "1.0.0",
        surface: "chat.agent",
        extensionId: "example.agent",
        classification: "unclassified",
        costUnits: null,
      },
    ],
    isLoading: false,
  }),
  useUpdateCapabilityCostPolicy: () => ({
    mutate: updateCapability,
    isPending: false,
  }),
  useAIUsage: () => ({
    data: { totalUnits: 0, charges: [] },
  }),
}))

import { AIControlsSection } from "./access-control-sections"

afterEach(() => {
  cleanup()
  updateCapability.mockReset()
})

describe("AI control setup safety", () => {
  it("keeps enforcement and classification submission disabled until an operator classifies the capability", () => {
    render(<AIControlsSection />)

    expect(screen.getByRole("switch", { name: "Enforce credits" })).toBeDisabled()
    expect(screen.getByRole("button", { name: "Classify" })).toBeDisabled()
    expect(screen.getAllByText("Unclassified").length).toBeGreaterThan(0)
    expect(updateCapability).not.toHaveBeenCalled()
  })
})
