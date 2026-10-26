import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

vi.mock("@/components/ui/chat/message-scroller", () => ({
  MessageScrollerItem: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
}));
vi.mock("@/components/ai-elements/persona", () => ({
  Persona: () => <div data-testid="persona" />,
}));
vi.mock("@/components/ai-elements/task", () => ({
  Task: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TaskTrigger: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TaskContent: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TaskItem: ({ children }: { children: React.ReactNode }) => <div>{children}</div>,
  TaskItemFile: ({ children }: { children: React.ReactNode }) => <span>{children}</span>,
}));

import { ChatMessage } from "./chat-message";
import type { Message } from "@/lib/chat-contract";

const callbacks = {
  onTaskOpenChange: vi.fn(),
  onOpenSources: vi.fn(),
  onPersonaLoad: vi.fn(),
  onOpenCanvas: vi.fn(),
  onResolveInterrupt: vi.fn(),
};

describe("ChatMessage", () => {
  it("keeps hook order stable when a streamed message gains an event", () => {
    const message: Message = {
      id: "message-1",
      role: "assistant",
      senderName: "Assistant",
      timestamp: "10:00",
      content: "Working",
      events: [],
    };
    const props = {
      isUser: false,
      userRole: "complete" as const,
      isTaskOpen: true,
      taskTimer: { elapsed: 1, completed: false },
      personaLoaded: true,
      ...callbacks,
    };

    const { rerender } = render(<ChatMessage message={message} {...props} />);

    expect(() => rerender(
      <ChatMessage
        message={{
          ...message,
          events: [{ type: "thought", content: "Checking data" }],
        }}
        {...props}
      />,
    )).not.toThrow();
    expect(screen.getByText("Checking data")).toBeInTheDocument();
  });
});
