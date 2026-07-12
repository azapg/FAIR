import * as React from "react";
import { RotateCcw } from "lucide-react";
import {
  MessageScroller,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/chat/message-scroller";
import { Button } from "@/components/ui/button";
import { ChatInput } from "@/components/chat/chat-input";
import { ChatMessage } from "@/components/chat/chat-message";
import { ElicitationPanel } from "@/components/chat/elicitation-panel";
import { useExecutionChat } from "@/hooks/use-execution-chat";

export default function LiveChatPage() {
  const live = useExecutionChat();
  const pending = live.pendingInteraction;
  const elicitation = pending
    ? {
        id: pending.id,
        questions: [
          {
            id: pending.id,
            title: pending.message,
            options:
              pending.choices?.map((choice) => {
                const value = String(choice.value ?? choice.label ?? "option");
                return { label: String(choice.label ?? value), value };
              }) ?? [{ label: "Continue", value: "continue" }],
          },
        ],
      }
    : null;

  return (
    <MessageScrollerProvider autoScroll>
      <div className="flex h-screen w-full flex-col bg-background">
        <header className="flex h-14 shrink-0 items-center justify-between border-b px-6">
          <div>
            <h1 className="text-sm font-semibold">FAIR live execution</h1>
            <p className="text-xs text-muted-foreground">
              {live.executionId ? `Execution ${live.executionId.slice(0, 8)} · ${live.status}` : "No active Execution"}
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={live.reset}>
            <RotateCcw className="mr-2 size-4" />
            Reset
          </Button>
        </header>

        <main className="min-h-0 flex-1">
          <MessageScroller className="flex h-full flex-col">
            <MessageScrollerViewport>
              <MessageScrollerContent className="mx-auto w-full max-w-3xl px-4 pb-36">
                {live.messages.length === 0 ? (
                  <MessageScrollerItem messageId="live-empty">
                    <div className="py-24 text-center text-sm text-muted-foreground">
                      Send a message to create a Thread, Turn, and durable Execution.
                    </div>
                  </MessageScrollerItem>
                ) : (
                  live.messages.map((message) => (
                    <ChatMessage
                      key={message.id}
                      message={message}
                      isUser={message.role === "user"}
                      userRole="complete"
                      isTaskOpen={false}
                      onTaskOpenChange={() => undefined}
                      onOpenSources={() => undefined}
                      taskTimer={{ elapsed: message.events?.length || 1, completed: live.status !== "streaming" }}
                      personaLoaded
                      onPersonaLoad={() => undefined}
                      onOpenCanvas={() => undefined}
                      onResolveInterrupt={() => undefined}
                      isCompletedResponse={live.status !== "streaming"}
                    />
                  ))
                )}
                {live.status === "streaming" && (
                  <MessageScrollerItem messageId="live-streaming">
                    <div className="py-3 text-sm text-muted-foreground">Waiting for Execution events…</div>
                  </MessageScrollerItem>
                )}
              </MessageScrollerContent>
            </MessageScrollerViewport>

            <div className="absolute inset-x-0 bottom-0 z-10 flex justify-center bg-gradient-to-t from-background via-background to-transparent p-4 pb-6">
              <div className="w-full max-w-[615px]">
                {elicitation && (
                  <ElicitationPanel
                    elicitation={elicitation}
                    onResolve={(_, value) => void live.resolve(pending!.id, value)}
                    onSkip={() => void live.resolve(pending!.id, "Skipped")}
                    onDismiss={() => void live.resolve(pending!.id, "Dismissed")}
                  />
                )}
                {live.error && (
                  <div className="mb-2 rounded-lg border border-destructive/30 bg-destructive/5 px-3 py-2 text-xs text-destructive">
                    {live.error}
                  </div>
                )}
                <ChatInput
                  onSend={(content) => void live.send(content)}
                  disabled={live.status === "streaming" || Boolean(pending)}
                  placeholder={pending ? "Awaiting your response above…" : "Ask the Execution service…"}
                />
              </div>
            </div>
          </MessageScroller>
        </main>
      </div>
    </MessageScrollerProvider>
  );
}
