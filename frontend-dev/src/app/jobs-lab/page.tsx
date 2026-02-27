import { useEffect, useMemo, useState } from "react";
import api, { getApiBaseUrl } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

type LogEntry = { ts: string; message: string };
type ExtensionRecord = {
  extensionId: string;
  webhookUrl: string;
  intents: string[];
  capabilities: string[];
  enabled: boolean;
};

function nowIso() {
  return new Date().toISOString();
}

function toJson(value: string, fallback: Record<string, unknown> = {}) {
  if (!value.trim()) return fallback;
  return JSON.parse(value) as Record<string, unknown>;
}

export default function JobsLabPage() {
  const [jobId, setJobId] = useState("");
  const [target, setTarget] = useState("mock.echo");
  const [payloadText, setPayloadText] = useState('{"text":"hello from Jobs Lab"}');
  const [metadataText, setMetadataText] = useState('{"source":"jobs-lab"}');
  const [updateEvent, setUpdateEvent] = useState("progress");
  const [updatePayload, setUpdatePayload] = useState('{"percent":50}');
  const [updateStatus, setUpdateStatus] = useState("running");
  const [stateOutput, setStateOutput] = useState("");
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [extensions, setExtensions] = useState<ExtensionRecord[]>([]);
  const [stream, setStream] = useState<EventSource | null>(null);

  const streamBase = useMemo(() => {
    const base = getApiBaseUrl();
    if (!base.startsWith("http")) return "";
    return base.replace(/\/api\/?$/, "");
  }, []);

  const appendLog = (message: string) =>
    setLogs((prev) => [...prev, { ts: nowIso(), message }]);

  const loadExtensions = async () => {
    try {
      const response = await api.get<ExtensionRecord[]>("/extensions/");
      setExtensions(response.data ?? []);
      appendLog(`extensions loaded: ${response.data?.length ?? 0}`);
    } catch (error: any) {
      appendLog(`extensions load failed: ${error?.message ?? String(error)}`);
    }
  };

  const openStreamForJob = (nextJobId: string) => {
    if (!nextJobId.trim()) return;
    if (stream) {
      stream.close();
      setStream(null);
    }
    const url = `${streamBase}/api/jobs/${nextJobId}/stream`;
    const source = new EventSource(url);
    source.onmessage = (evt) => appendLog(`stream message: ${evt.data}`);
    source.onerror = () => appendLog("stream error/disconnected");
    source.addEventListener("progress", (evt) => {
      const data = (evt as MessageEvent).data ?? "";
      appendLog(`stream progress: ${data}`);
    });
    source.addEventListener("result", (evt) => {
      const data = (evt as MessageEvent).data ?? "";
      appendLog(`stream result: ${data}`);
    });
    setStream(source);
    appendLog(`stream opened for ${nextJobId}`);
  };

  const createJob = async () => {
    try {
      const response = await api.post("/jobs/", {
        jobId: jobId.trim() || undefined,
        target,
        payload: toJson(payloadText),
        metadata: toJson(metadataText),
      });
      const nextJobId = response.data.jobId as string;
      setJobId(nextJobId);
      appendLog(`job created: ${JSON.stringify(response.data)}`);
      openStreamForJob(nextJobId);
    } catch (error: any) {
      appendLog(`create failed: ${error?.message ?? String(error)}`);
    }
  };

  const fetchState = async () => {
    if (!jobId.trim()) return;
    try {
      const response = await api.get(`/jobs/${jobId}`);
      setStateOutput(JSON.stringify(response.data, null, 2));
      appendLog(`state fetched: ${response.data.status}`);
    } catch (error: any) {
      appendLog(`state failed: ${error?.message ?? String(error)}`);
    }
  };

  const sendUpdate = async () => {
    if (!jobId.trim()) return;
    try {
      const response = await api.post(`/jobs/${jobId}/updates`, {
        event: updateEvent,
        payload: toJson(updatePayload),
        status: updateStatus || undefined,
      });
      appendLog(`update posted: ${JSON.stringify(response.data)}`);
    } catch (error: any) {
      appendLog(`update failed: ${error?.message ?? String(error)}`);
    }
  };

  const openStream = () => {
    if (!jobId.trim() || stream) return;
    openStreamForJob(jobId);
  };

  const closeStream = () => {
    if (!stream) return;
    stream.close();
    setStream(null);
    appendLog("stream closed");
  };

  useEffect(() => {
    void loadExtensions();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto w-full max-w-6xl space-y-4 p-6">
      <h1 className="text-2xl font-semibold">Jobs Lab</h1>
      <p className="text-sm text-muted-foreground">
        Manual communications test page for extension registration, job creation, updates, and SSE streaming.
      </p>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Extensions Registry</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Button onClick={loadExtensions}>Refresh Registry</Button>
            </div>
            <div className="max-h-72 space-y-2 overflow-auto rounded-md border p-2 text-xs">
              {extensions.length === 0 && (
                <div className="text-muted-foreground">
                  No registered extensions. Start your mock extension with `--auto-register` and refresh.
                </div>
              )}
              {extensions.map((ext) => (
                <div key={ext.extensionId} className="rounded border p-2">
                  <div className="flex items-center gap-2">
                    <span className="font-semibold">{ext.extensionId}</span>
                    <span className="text-muted-foreground">{ext.enabled ? "enabled" : "disabled"}</span>
                    <Button
                      size="sm"
                      variant="outline"
                      className="ml-auto h-6 px-2 text-xs"
                      onClick={() => {
                        setTarget(ext.extensionId);
                        appendLog(`target set from registry: ${ext.extensionId}`);
                      }}
                    >
                      Use target
                    </Button>
                  </div>
                  <div className="text-muted-foreground">{ext.webhookUrl}</div>
                  <div>intents: {ext.intents.join(", ") || "-"}</div>
                  <div>capabilities: {ext.capabilities.join(", ") || "-"}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Create Job</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Label htmlFor="job-id">Job ID (optional)</Label>
            <Input id="job-id" value={jobId} onChange={(e) => setJobId(e.target.value)} />
            <Label htmlFor="target">Target Extension</Label>
            <Input id="target" value={target} onChange={(e) => setTarget(e.target.value)} />
            <Label htmlFor="payload">Payload JSON</Label>
            <Textarea id="payload" value={payloadText} onChange={(e) => setPayloadText(e.target.value)} />
            <Label htmlFor="metadata">Metadata JSON</Label>
            <Textarea id="metadata" value={metadataText} onChange={(e) => setMetadataText(e.target.value)} />
            <Button onClick={createJob}>Create Job</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>State / Updates</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex gap-2">
              <Button variant="secondary" onClick={fetchState}>Fetch State</Button>
              <Button variant="outline" onClick={openStream} disabled={!!stream}>Open Stream</Button>
              <Button variant="outline" onClick={closeStream} disabled={!stream}>Close Stream</Button>
            </div>
            <Label htmlFor="update-event">Update Event</Label>
            <Input id="update-event" value={updateEvent} onChange={(e) => setUpdateEvent(e.target.value)} />
            <Label htmlFor="update-status">Update Status (optional)</Label>
            <Input id="update-status" value={updateStatus} onChange={(e) => setUpdateStatus(e.target.value)} />
            <Label htmlFor="update-payload">Update Payload JSON</Label>
            <Textarea id="update-payload" value={updatePayload} onChange={(e) => setUpdatePayload(e.target.value)} />
            <Button onClick={sendUpdate}>POST Update</Button>
            <pre className="max-h-64 overflow-auto rounded-md bg-muted p-3 text-xs">{stateOutput || "No state fetched yet."}</pre>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Event Log</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-96 space-y-1 overflow-auto rounded-md border p-2 text-xs">
              {logs.length === 0 && <div className="text-muted-foreground">No events yet.</div>}
              {logs.map((entry, idx) => (
                <div key={`${entry.ts}-${idx}`}>
                  <span className="text-muted-foreground">{entry.ts}</span>{" "}
                  <span>{entry.message}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
