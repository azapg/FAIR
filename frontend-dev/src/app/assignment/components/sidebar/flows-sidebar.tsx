import { useEffect, useMemo, useState } from "react";
import { Play, PlusIcon, Waypoints } from "lucide-react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar";
import {
  latestPublishedVersion,
  useCreateFlow,
  useFlows,
  useStartFlow,
} from "@/hooks/use-flows";
import { useSubmissions } from "@/hooks/use-submissions";

export function FlowsSidebar({
  side,
  courseId,
  assignmentId,
}: {
  side?: "left" | "right";
  courseId: string;
  assignmentId: string;
}) {
  const { data: flows = [], isLoading } = useFlows(courseId);
  const { data: submissions = [] } = useSubmissions({ assignment_id: assignmentId });
  const createFlow = useCreateFlow();
  const startFlow = useStartFlow();
  const [selectedId, setSelectedId] = useState<string>();

  useEffect(() => {
    if (!selectedId && flows[0]) setSelectedId(flows[0].id);
    if (selectedId && !flows.some((flow) => flow.id === selectedId)) {
      setSelectedId(flows[0]?.id);
    }
  }, [flows, selectedId]);

  const selected = useMemo(
    () => flows.find((flow) => flow.id === selectedId),
    [flows, selectedId],
  );
  const version = latestPublishedVersion(selected);

  async function create() {
    const name = prompt("Flow name", "Untitled Flow")?.trim();
    if (!name) return;
    const flow = await createFlow.mutateAsync({ name, courseId });
    setSelectedId(flow.id);
  }

  async function run() {
    if (!selected || !version) return;
    try {
      await startFlow.mutateAsync({
        flowId: selected.id,
        flowVersionId: version.id,
        assignmentId,
        submissionIds: submissions.map((submission) => submission.id),
      });
      toast.success("Flow execution started");
    } catch (error) {
      toast.error("Flow could not start", {
        description: error instanceof Error ? error.message : undefined,
      });
    }
  }

  return (
    <Sidebar side={side}>
      <SidebarHeader className="flex-row items-center gap-2 px-2.5 py-4">
        <Select value={selectedId} onValueChange={setSelectedId}>
          <SelectTrigger className="w-full">
            <SelectValue placeholder={isLoading ? "Loading flows…" : "Select a flow"} />
          </SelectTrigger>
          <SelectContent position="popper">
            {flows.map((flow) => (
              <SelectItem key={flow.id} value={flow.id}>
                {flow.name}
              </SelectItem>
            ))}
            {!flows.length && (
              <SelectItem value="no-flows" disabled>
                No flows yet
              </SelectItem>
            )}
          </SelectContent>
        </Select>
        <Button variant="outline" size="icon" onClick={create}>
          <PlusIcon />
        </Button>
      </SidebarHeader>
      <Separator />
      <SidebarContent>
        <ScrollArea className="h-full p-4">
          {!selected ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-center text-sm text-muted-foreground">
              <Waypoints />
              Create a Flow, then publish an ordered version through the FAIR API.
            </div>
          ) : !version ? (
            <p className="text-sm text-muted-foreground">
              This Flow has no published version yet. Drafts cannot be executed.
            </p>
          ) : (
            <div className="space-y-3">
              <div>
                <p className="font-medium">Published version {version.ordinal}</p>
                <p className="text-xs text-muted-foreground break-all">
                  {version.definitionHash}
                </p>
              </div>
              <ol className="space-y-2">
                {version.definition.nodes.map((node, index) => (
                  <li key={node.id} className="rounded-md border p-2 text-sm">
                    <span className="mr-2 text-muted-foreground">{index + 1}.</span>
                    {node.id}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </ScrollArea>
      </SidebarContent>
      <SidebarFooter className="px-2.5 py-3">
        <Button
          onClick={run}
          disabled={!version || startFlow.isPending}
          className="w-full"
        >
          <Play /> {startFlow.isPending ? "Starting…" : "Run published Flow"}
        </Button>
      </SidebarFooter>
    </Sidebar>
  );
}
