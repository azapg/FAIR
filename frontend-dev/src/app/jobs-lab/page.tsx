import { useEffect, useMemo, useRef, useState } from "react";
import { Ellipsis, Loader2, CircleCheck, CircleX, Ban, Circle } from "lucide-react";
import api, { getApiBaseUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type LogEntry = { ts: string; message: string };
type ExtensionRecord = {
  extensionId: string;
  webhookUrl: string;
  intents: string[];
  capabilities: string[];
  enabled: boolean;
};
type JobEntry = {
  jobId: string;
  target: string;
  status: string;
  updatedAt: string;
  isStreaming: boolean;
  lastEvent: string;
};

const TERMINAL_STATUSES = new Set(["completed", "failed", "cancelled"]);

function nowIso() {
  return new Date().toISOString();
}

function toJson(value: string, fallback: Record<string, unknown> = {}) {
  if (!value.trim()) return fallback;
  return JSON.parse(value) as Record<string, unknown>;
}

function apiRootUrl() {
  const base = getApiBaseUrl();
  if (base.startsWith("http")) return base.replace(/\/api\/?$/, "");
  return "";
}

function JobStatusBadge({ status }: { status: string }) {
  const normalized = status.toLowerCase();
  if (normalized === "completed") {
    return (
      <Badge className="gap-1 bg-emerald-500/15 text-emerald-700 hover:bg-emerald-500/15">
        <CircleCheck size={12} /> completed
      </Badge>
    );
  }
  if (normalized === "failed") {
    return (
      <Badge className="gap-1 bg-rose-500/15 text-rose-700 hover:bg-rose-500/15">
        <CircleX size={12} /> failed
      </Badge>
    );
  }
  if (normalized === "cancelled") {
    return (
      <Badge className="gap-1 bg-slate-500/15 text-slate-700 hover:bg-slate-500/15">
        <Ban size={12} /> cancelled
      </Badge>
    );
  }
  if (normalized === "running") {
    return (
      <Badge className="gap-1 bg-amber-500/15 text-amber-700 hover:bg-amber-500/15">
        <Loader2 size={12} className="animate-spin" /> running
      </Badge>
    );
  }
  return (
    <Badge className="gap-1 bg-blue-500/15 text-blue-700 hover:bg-blue-500/15">
      <Circle size={12} /> {normalized}
    </Badge>
  );
}

function StreamStatusBadge({ isStreaming }: { isStreaming: boolean }) {
  return isStreaming ? (
    <Badge className="gap-1 bg-amber-500/15 text-amber-700 hover:bg-amber-500/15">
      <Loader2 size={12} className="animate-spin" /> streaming
    </Badge>
  ) : (
    <Badge variant="outline" className="gap-1">
      <Circle size={12} /> idle
    </Badge>
  );
}

export default function JobsLabPage() {
  const [autoGenerateJobId, setAutoGenerateJobId] = useState(true);
  const [manualJobId, setManualJobId] = useState("");
  const [payloadText, setPayloadText] = useState('{"text":"hello from Jobs Lab"}');
  const [metadataText, setMetadataText] = useState('{"source":"jobs-lab"}');

  const [extensions, setExtensions] = useState<ExtensionRecord[]>([]);
  const [targetExtensionId, setTargetExtensionId] = useState("");
  const [createAdvancedOpen, setCreateAdvancedOpen] = useState(false);
  const [createCustomExtensions, setCreateCustomExtensions] = useState(false);
  const [customTargetExtensionId, setCustomTargetExtensionId] = useState("");

  const [jobs, setJobs] = useState<JobEntry[]>([]);
  const [selectedJobId, setSelectedJobId] = useState("");

  const [updateJobId, setUpdateJobId] = useState("");
  const [updateEvent, setUpdateEvent] = useState("progress");
  const [updatePayload, setUpdatePayload] = useState('{"percent":50}');
  const [updateStatus, setUpdateStatus] = useState("running");
  const [updateExtensionId, setUpdateExtensionId] = useState("");
  const [updateExtensionSecret, setUpdateExtensionSecret] = useState("");
  const [updateAdvancedOpen, setUpdateAdvancedOpen] = useState(false);
  const [updateCustomExtensions, setUpdateCustomExtensions] = useState(false);
  const [updateCustomExtensionId, setUpdateCustomExtensionId] = useState("");

  const [stateOutput, setStateOutput] = useState("No state yet.");
  const [logs, setLogs] = useState<LogEntry[]>([]);

  const streamControllersRef = useRef<Map<string, AbortController>>(new Map());
  const pollTimersRef = useRef<Map<string, number>>(new Map());

  const appendLog = (message: string) =>
    setLogs((prev) => [...prev, { ts: nowIso(), message }]);

  const resolvedTargetExtensionId = createCustomExtensions
    ? customTargetExtensionId.trim()
    : targetExtensionId.trim();
  const resolvedUpdateExtensionId = updateCustomExtensions
    ? updateCustomExtensionId.trim()
    : updateExtensionId.trim();

  const sortedJobs = useMemo(
    () => [...jobs].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    [jobs],
  );

  const upsertJob = (next: JobEntry) => {
    setJobs((current) => {
      const without = current.filter((item) => item.jobId !== next.jobId);
      return [next, ...without];
    });
  };

  const patchJob = (jobId: string, patch: Partial<JobEntry>) => {
    setJobs((current) =>
      current.map((item) => (item.jobId === jobId ? { ...item, ...patch } : item)),
    );
  };

  const loadExtensions = async () => {
    try {
      const response = await api.get<ExtensionRecord[]>("/extensions/");
      const list = response.data ?? [];
      setExtensions(list);
      if (!targetExtensionId && list.length > 0) setTargetExtensionId(list[0].extensionId);
      if (!updateExtensionId && list.length > 0) setUpdateExtensionId(list[0].extensionId);
      appendLog(`extensions loaded: ${list.length}`);
    } catch (error: any) {
      appendLog(`extensions load failed: ${error?.message ?? String(error)}`);
    }
  };

  const stopPolling = (jobId: string) => {
    const timer = pollTimersRef.current.get(jobId);
    if (timer !== undefined) {
      window.clearInterval(timer);
      pollTimersRef.current.delete(jobId);
    }
  };

  const stopStream = (jobId: string, reason?: string) => {
    const controller = streamControllersRef.current.get(jobId);
    if (controller) {
      controller.abort();
      streamControllersRef.current.delete(jobId);
    }
    stopPolling(jobId);
    patchJob(jobId, { isStreaming: false, updatedAt: nowIso() });
    if (reason) appendLog(`${jobId}: ${reason}`);
  };

  const refreshJobState = async (jobId: string) => {
    try {
      const response = await api.get(`/jobs/${jobId}`);
      const state = response.data as {
        status?: string;
        updatedAt?: string;
      };
      const status = state.status ?? "unknown";
      patchJob(jobId, {
        status,
        updatedAt: state.updatedAt ?? nowIso(),
        lastEvent: `state:${status}`,
      });
      setStateOutput(JSON.stringify(response.data, null, 2));
      if (TERMINAL_STATUSES.has(status)) {
        stopStream(jobId, `${jobId}: terminal state reached (${status})`);
      }
    } catch (error: any) {
      appendLog(`${jobId}: state refresh failed: ${error?.message ?? String(error)}`);
    }
  };

  const startStatePolling = (jobId: string) => {
    stopPolling(jobId);
    const timer = window.setInterval(() => {
      void refreshJobState(jobId);
    }, 1000);
    pollTimersRef.current.set(jobId, timer);
  };

  const startStream = async (jobId: string) => {
    if (!jobId.trim()) return;
    stopStream(jobId);

    const token = localStorage.getItem("token");
    if (!token) {
      appendLog(`${jobId}: stream failed (no user token)`);
      return;
    }

    const controller = new AbortController();
    streamControllersRef.current.set(jobId, controller);
    patchJob(jobId, { isStreaming: true, updatedAt: nowIso() });
    startStatePolling(jobId);
    appendLog(`${jobId}: stream opening`);

    try {
      const root = apiRootUrl();
      const streamUrl = root
        ? `${root}/api/jobs/${encodeURIComponent(jobId)}/stream`
        : `/api/jobs/${encodeURIComponent(jobId)}/stream`;
      const response = await fetch(streamUrl, {
        method: "GET",
        headers: { Authorization: `Bearer ${token}` },
        signal: controller.signal,
      });
      if (!response.ok || !response.body) {
        appendLog(`${jobId}: stream failed HTTP ${response.status}`);
        stopStream(jobId);
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() ?? "";

        for (const block of blocks) {
          const lines = block.split("\n");
          let eventName = "message";
          const dataLines: string[] = [];
          for (const line of lines) {
            if (line.startsWith(":")) continue;
            if (line.startsWith("event:")) eventName = line.slice(6).trim() || "message";
            if (line.startsWith("data:")) dataLines.push(line.slice(5).trim());
          }
          if (dataLines.length === 0) continue;
          const rawData = dataLines.join("\n");
          patchJob(jobId, { lastEvent: eventName, updatedAt: nowIso() });
          appendLog(`${jobId}: ${eventName} ${rawData}`);
          setStateOutput(rawData);
          if (eventName === "end") {
            stopStream(jobId, `${jobId}: stream ended`);
            return;
          }
        }
      }

      stopStream(jobId, `${jobId}: stream closed by server`);
    } catch (error: any) {
      if (controller.signal.aborted) return;
      appendLog(`${jobId}: stream error ${error?.message ?? String(error)}`);
      stopStream(jobId);
    }
  };

  const createJob = async () => {
    if (!resolvedTargetExtensionId) {
      appendLog("create failed: target extension is required");
      return;
    }
    if (!autoGenerateJobId && !manualJobId.trim()) {
      appendLog("create failed: job id is required when auto-generate is disabled");
      return;
    }
    try {
      const response = await api.post("/jobs/", {
        jobId: autoGenerateJobId ? undefined : manualJobId.trim(),
        target: resolvedTargetExtensionId,
        payload: toJson(payloadText),
        metadata: toJson(metadataText),
      });
      const createdJobId = response.data.jobId as string;
      upsertJob({
        jobId: createdJobId,
        target: resolvedTargetExtensionId,
        status: response.data.status ?? "queued",
        updatedAt: nowIso(),
        isStreaming: false,
        lastEvent: "created",
      });
      setSelectedJobId(createdJobId);
      setUpdateJobId(createdJobId);
      if (!autoGenerateJobId) setManualJobId("");
      appendLog(`job created: ${createdJobId}`);
      await startStream(createdJobId);
    } catch (error: any) {
      appendLog(`create failed: ${error?.message ?? String(error)}`);
    }
  };

  const sendUpdate = async () => {
    if (!updateJobId.trim()) {
      appendLog("update failed: select a job");
      return;
    }
    if (!resolvedUpdateExtensionId) {
      appendLog("update failed: extension id is required");
      return;
    }
    if (!updateExtensionSecret.trim()) {
      appendLog("update failed: extension secret is required");
      return;
    }
    try {
      const response = await api.post(
        `/jobs/${encodeURIComponent(updateJobId)}/updates`,
        {
          event: updateEvent.trim(),
          payload: toJson(updatePayload),
          status: updateStatus.trim() || undefined,
        },
        {
          headers: {
            "X-FAIR-Extension-Id": resolvedUpdateExtensionId,
            Authorization: `Bearer ${updateExtensionSecret.trim()}`,
          },
        },
      );
      appendLog(`${updateJobId}: update posted ${JSON.stringify(response.data)}`);
      await refreshJobState(updateJobId);
    } catch (error: any) {
      appendLog(`${updateJobId}: update failed ${error?.message ?? String(error)}`);
    }
  };

  useEffect(() => {
    void loadExtensions();
    return () => {
      for (const [jobId, controller] of streamControllersRef.current.entries()) {
        controller.abort();
        streamControllersRef.current.delete(jobId);
      }
      for (const [jobId, timer] of pollTimersRef.current.entries()) {
        window.clearInterval(timer);
        pollTimersRef.current.delete(jobId);
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5 p-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Jobs Lab</h1>
        <p className="text-sm text-muted-foreground">
          Create many jobs, stream them independently, and send extension updates to selected jobs.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-1">
          <CardHeader>
            <CardTitle>Create Job</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label htmlFor="manual-job-id">Job ID</Label>
                <Input
                  id="manual-job-id"
                  disabled={autoGenerateJobId}
                  placeholder={autoGenerateJobId ? "Generated on create" : "Required"}
                  value={manualJobId}
                  onChange={(e) => setManualJobId(e.target.value)}
                />
              </div>

              <div className="space-y-1.5">
                <Label>Target Extension</Label>
                <Select
                  value={targetExtensionId || undefined}
                  onValueChange={setTargetExtensionId}
                  disabled={createCustomExtensions || extensions.length === 0}
                >
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Select extension" />
                  </SelectTrigger>
                  <SelectContent>
                    {extensions.map((ext) => (
                      <SelectItem key={ext.extensionId} value={ext.extensionId}>
                        {ext.extensionId}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="payload">Payload JSON</Label>
                <Textarea id="payload" value={payloadText} onChange={(e) => setPayloadText(e.target.value)} />
              </div>

              <div className="space-y-1.5">
                <Label htmlFor="metadata">Metadata JSON</Label>
                <Textarea id="metadata" value={metadataText} onChange={(e) => setMetadataText(e.target.value)} />
              </div>

              <Collapsible open={createAdvancedOpen} onOpenChange={setCreateAdvancedOpen}>
                <CollapsibleTrigger asChild>
                  <button
                    type="button"
                    className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                  >
                    Advanced settings
                  </button>
                </CollapsibleTrigger>
                <CollapsibleContent className="mt-2 space-y-2">
                  <div className="flex items-center justify-between">
                    <Label htmlFor="auto-generate-id">Auto-generate Job ID</Label>
                    <Switch
                      id="auto-generate-id"
                      checked={autoGenerateJobId}
                      onCheckedChange={setAutoGenerateJobId}
                    />
                  </div>
                  <div className="flex items-center justify-between">
                    <Label htmlFor="create-custom-extensions">Custom Extensions</Label>
                    <Switch
                      id="create-custom-extensions"
                      checked={createCustomExtensions}
                      onCheckedChange={setCreateCustomExtensions}
                    />
                  </div>
                  {createCustomExtensions && (
                    <div className="space-y-1.5">
                      <Label htmlFor="custom-target-id">Custom Target Extension ID</Label>
                      <Input
                        id="custom-target-id"
                        value={customTargetExtensionId}
                        onChange={(e) => setCustomTargetExtensionId(e.target.value)}
                      />
                    </div>
                  )}
                </CollapsibleContent>
              </Collapsible>

              <Button onClick={createJob} className="w-full">Create</Button>
            </div>
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <CardTitle>Jobs</CardTitle>
            <Button variant="outline" onClick={() => void loadExtensions()}>
              Refresh Extensions
            </Button>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[430px] rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Job ID</TableHead>
                    <TableHead>Target</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Stream</TableHead>
                    <TableHead>Updated</TableHead>
                    <TableHead className="w-10 text-right">
                      <Ellipsis size={14} className="ml-auto text-muted-foreground" />
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedJobs.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-muted-foreground">
                        No jobs created yet.
                      </TableCell>
                    </TableRow>
                  )}
                  {sortedJobs.map((job) => (
                    <TableRow
                      key={job.jobId}
                      data-state={selectedJobId === job.jobId ? "selected" : undefined}
                      onClick={() => setSelectedJobId(job.jobId)}
                      className="cursor-pointer"
                    >
                      <TableCell className="font-mono text-xs">{job.jobId}</TableCell>
                      <TableCell>{job.target}</TableCell>
                      <TableCell>
                        <JobStatusBadge status={job.status} />
                      </TableCell>
                      <TableCell>
                        <StreamStatusBadge isStreaming={job.isStreaming} />
                      </TableCell>
                      <TableCell className="text-xs">{job.updatedAt}</TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger className="cursor-pointer" onClick={(e) => e.stopPropagation()}>
                            <Ellipsis size={18} />
                          </DropdownMenuTrigger>
                          <DropdownMenuContent onClick={(e) => e.stopPropagation()}>
                            <DropdownMenuItem onClick={() => void startStream(job.jobId)}>
                              Start Stream
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => stopStream(job.jobId, `${job.jobId}: stream stopped`)}>
                              Stop Stream
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => void refreshJobState(job.jobId)}>
                              Refresh State
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => {
                                setUpdateJobId(job.jobId);
                                setSelectedJobId(job.jobId);
                              }}
                            >
                              Use in Updater
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => void navigator.clipboard.writeText(job.jobId)}>
                              Copy Job ID
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Extension Job Updater</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[420px] pr-3">
              <div className="space-y-3">
                <div className="space-y-1.5">
                  <Label>Job</Label>
                  <Select value={updateJobId || undefined} onValueChange={setUpdateJobId}>
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select existing job" />
                    </SelectTrigger>
                    <SelectContent>
                      {sortedJobs.map((job) => (
                        <SelectItem key={job.jobId} value={job.jobId}>
                          {job.jobId}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-1.5">
                  <Label>Extension ID</Label>
                  <Select
                    value={updateExtensionId || undefined}
                    onValueChange={setUpdateExtensionId}
                    disabled={updateCustomExtensions || extensions.length === 0}
                  >
                    <SelectTrigger className="w-full">
                      <SelectValue placeholder="Select extension" />
                    </SelectTrigger>
                    <SelectContent>
                      {extensions.map((ext) => (
                        <SelectItem key={ext.extensionId} value={ext.extensionId}>
                          {ext.extensionId}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <Collapsible open={updateAdvancedOpen} onOpenChange={setUpdateAdvancedOpen}>
                  <CollapsibleTrigger asChild>
                    <button
                      type="button"
                      className="text-xs text-muted-foreground hover:text-foreground transition-colors"
                    >
                      Advanced settings
                    </button>
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-2 space-y-2">
                    <div className="flex items-center justify-between">
                      <Label htmlFor="update-custom-extensions">Custom Extensions</Label>
                      <Switch
                        id="update-custom-extensions"
                        checked={updateCustomExtensions}
                        onCheckedChange={setUpdateCustomExtensions}
                      />
                    </div>
                    {updateCustomExtensions && (
                      <div className="space-y-1.5">
                        <Label htmlFor="update-custom-extension-id">Custom Extension ID</Label>
                        <Input
                          id="update-custom-extension-id"
                          value={updateCustomExtensionId}
                          onChange={(e) => setUpdateCustomExtensionId(e.target.value)}
                        />
                      </div>
                    )}
                  </CollapsibleContent>
                </Collapsible>

                <div className="space-y-1.5">
                  <Label htmlFor="update-secret">Extension Secret</Label>
                  <Input
                    id="update-secret"
                    type="password"
                    value={updateExtensionSecret}
                    onChange={(e) => setUpdateExtensionSecret(e.target.value)}
                  />
                </div>

                <div className="grid gap-3 md:grid-cols-2">
                  <div className="space-y-1.5">
                    <Label htmlFor="update-event">Event</Label>
                    <Input id="update-event" value={updateEvent} onChange={(e) => setUpdateEvent(e.target.value)} />
                  </div>
                  <div className="space-y-1.5">
                    <Label htmlFor="update-status">Status (optional)</Label>
                    <Input id="update-status" value={updateStatus} onChange={(e) => setUpdateStatus(e.target.value)} />
                  </div>
                </div>

                <div className="space-y-1.5">
                  <Label htmlFor="update-payload">Payload JSON</Label>
                  <Textarea id="update-payload" value={updatePayload} onChange={(e) => setUpdatePayload(e.target.value)} />
                </div>

                <Button onClick={sendUpdate} className="w-full">
                  Send Job Update
                </Button>
              </div>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="xl:col-span-1">
          <CardHeader>
            <CardTitle>Extensions</CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[420px] rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="w-10 text-right">
                      <Ellipsis size={14} className="ml-auto text-muted-foreground" />
                    </TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {extensions.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={3} className="text-muted-foreground">
                        No registered extensions.
                      </TableCell>
                    </TableRow>
                  )}
                  {extensions.map((ext) => (
                    <TableRow key={ext.extensionId}>
                      <TableCell>{ext.extensionId}</TableCell>
                      <TableCell>
                        <Badge variant={ext.enabled ? "default" : "outline"}>
                          {ext.enabled ? "enabled" : "disabled"}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        <DropdownMenu>
                          <DropdownMenuTrigger className="cursor-pointer">
                            <Ellipsis size={18} />
                          </DropdownMenuTrigger>
                          <DropdownMenuContent>
                            <DropdownMenuItem
                              onClick={() => {
                                setCreateCustomExtensions(false);
                                setTargetExtensionId(ext.extensionId);
                              }}
                            >
                              Use as Target
                            </DropdownMenuItem>
                            <DropdownMenuItem
                              onClick={() => {
                                setUpdateCustomExtensions(false);
                                setUpdateExtensionId(ext.extensionId);
                              }}
                            >
                              Use as Updater Extension
                            </DropdownMenuItem>
                            <DropdownMenuItem onClick={() => void navigator.clipboard.writeText(ext.extensionId)}>
                              Copy Extension ID
                            </DropdownMenuItem>
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </ScrollArea>
          </CardContent>
        </Card>

        <Card className="xl:col-span-3">
          <CardHeader>
            <CardTitle>Live Output</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-4 xl:grid-cols-2">
            <ScrollArea className="h-[260px] rounded-md border bg-muted p-3">
              <pre className="text-xs whitespace-pre-wrap break-words">{stateOutput}</pre>
            </ScrollArea>
            <ScrollArea className="h-[260px] rounded-md border p-2">
              <div className="space-y-1 text-xs">
                {logs.length === 0 && <div className="text-muted-foreground">No events yet.</div>}
                {logs.map((entry, idx) => (
                  <div key={`${entry.ts}-${idx}`}>
                    <span className="text-muted-foreground">{entry.ts}</span>{" "}
                    <span>{entry.message}</span>
                  </div>
                ))}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
