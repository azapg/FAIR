import { useEffect, useMemo, useState } from "react";
import api from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

type ExtensionClientRead = {
  extensionId: string;
  scopes: string[];
  enabled: boolean;
  createdAt: string;
  updatedAt: string;
};

type ExtensionClientSecretRead = {
  extensionId: string;
  extensionSecret: string;
  scopes: string[];
  enabled: boolean;
};

type StoredCredential = {
  extensionId: string;
  extensionSecret: string;
  scopes: string[];
  updatedAt: string;
};

const CREDENTIALS_STORAGE_KEY = "admin-lab:extension-credentials";

function parseScopes(input: string): string[] {
  return Array.from(
    new Set(
      input
        .split(",")
        .map((value) => value.trim())
        .filter(Boolean),
    ),
  );
}

function tryReadStoredCredentials(): StoredCredential[] {
  try {
    const raw = localStorage.getItem(CREDENTIALS_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as StoredCredential[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeStoredCredentials(creds: StoredCredential[]) {
  localStorage.setItem(CREDENTIALS_STORAGE_KEY, JSON.stringify(creds));
}

export default function AdminLabPage() {
  const [extensionId, setExtensionId] = useState("mock.echo");
  const [scopesText, setScopesText] = useState("jobs:read,jobs:write,extensions:connect");
  const [clients, setClients] = useState<ExtensionClientRead[]>([]);
  const [credentials, setCredentials] = useState<StoredCredential[]>([]);
  const [lastIssued, setLastIssued] = useState<ExtensionClientSecretRead | null>(null);
  const [log, setLog] = useState<string[]>([]);

  const appendLog = (message: string) => {
    const ts = new Date().toISOString();
    setLog((current) => [...current, `${ts} ${message}`]);
  };

  const sortedCredentials = useMemo(
    () => [...credentials].sort((a, b) => b.updatedAt.localeCompare(a.updatedAt)),
    [credentials],
  );

  const upsertCredential = (payload: ExtensionClientSecretRead) => {
    const next: StoredCredential = {
      extensionId: payload.extensionId,
      extensionSecret: payload.extensionSecret,
      scopes: payload.scopes,
      updatedAt: new Date().toISOString(),
    };
    setCredentials((current) => {
      const filtered = current.filter((item) => item.extensionId !== next.extensionId);
      const merged = [next, ...filtered];
      writeStoredCredentials(merged);
      return merged;
    });
  };

  const removeStoredCredential = (id: string) => {
    setCredentials((current) => {
      const filtered = current.filter((item) => item.extensionId !== id);
      writeStoredCredentials(filtered);
      return filtered;
    });
    appendLog(`removed local credential for ${id}`);
  };

  const loadClients = async () => {
    try {
      const response = await api.get<ExtensionClientRead[]>("/extensions/admin/clients");
      setClients(response.data ?? []);
      appendLog(`loaded ${response.data?.length ?? 0} server clients`);
    } catch (error: any) {
      appendLog(`load failed: ${error?.message ?? String(error)}`);
    }
  };

  const issueClient = async () => {
    const trimmedId = extensionId.trim();
    if (!trimmedId) return;
    try {
      const response = await api.post<ExtensionClientSecretRead>("/extensions/admin/clients", {
        extensionId: trimmedId,
        scopes: parseScopes(scopesText),
        enabled: true,
      });
      setLastIssued(response.data);
      upsertCredential(response.data);
      appendLog(`issued secret for ${response.data.extensionId}`);
      await loadClients();
    } catch (error: any) {
      appendLog(`issue failed: ${error?.message ?? String(error)}`);
    }
  };

  const rotateSecret = async (id?: string) => {
    const resolvedId = (id ?? extensionId).trim();
    if (!resolvedId) return;
    try {
      const response = await api.post<ExtensionClientSecretRead>(
        `/extensions/admin/clients/${encodeURIComponent(resolvedId)}/rotate`,
      );
      setLastIssued(response.data);
      upsertCredential(response.data);
      appendLog(`rotated secret for ${response.data.extensionId}`);
      await loadClients();
    } catch (error: any) {
      appendLog(`rotate failed: ${error?.message ?? String(error)}`);
    }
  };

  const copySecret = async (secret: string, id: string) => {
    try {
      await navigator.clipboard.writeText(secret);
      appendLog(`copied secret for ${id}`);
    } catch (error: any) {
      appendLog(`copy failed for ${id}: ${error?.message ?? String(error)}`);
    }
  };

  useEffect(() => {
    setCredentials(tryReadStoredCredentials());
    void loadClients();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="mx-auto w-full max-w-7xl space-y-5 p-6">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">Admin Lab</h1>
        <p className="text-sm text-muted-foreground">
          Manage extension clients and keep a local credential vault for testing multiple extensions.
        </p>
      </div>

      <div className="grid gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-1">
          <CardHeader>
            <CardTitle>Issue / Rotate</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="space-y-1.5">
              <Label htmlFor="extension-id">Extension ID</Label>
              <Input
                id="extension-id"
                value={extensionId}
                onChange={(event) => setExtensionId(event.target.value)}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="scopes">Scopes (comma-separated)</Label>
              <Textarea
                id="scopes"
                value={scopesText}
                onChange={(event) => setScopesText(event.target.value)}
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <Button onClick={issueClient}>Issue Secret</Button>
              <Button variant="secondary" onClick={() => void rotateSecret()}>
                Rotate Secret
              </Button>
              <Button variant="outline" onClick={loadClients}>Refresh Server Clients</Button>
            </div>
            <div className="rounded-md border bg-muted p-3 text-xs">
              {lastIssued ? (
                <div className="space-y-2">
                  <div className="flex items-center gap-2">
                    <span className="font-medium">{lastIssued.extensionId}</span>
                    <Badge variant="outline">{lastIssued.enabled ? "enabled" : "disabled"}</Badge>
                  </div>
                  <div className="break-all font-mono">{lastIssued.extensionSecret}</div>
                  <div className="text-muted-foreground">
                    scopes: {lastIssued.scopes.join(", ") || "-"}
                  </div>
                </div>
              ) : (
                "No secret issued in this session."
              )}
            </div>
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Local Credential Vault</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Stored only in this browser to support testing multiple extensions without re-issuing constantly.
            </p>
            <div className="max-h-80 overflow-auto rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Extension</TableHead>
                    <TableHead>Scopes</TableHead>
                    <TableHead>Updated</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {sortedCredentials.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={4} className="text-muted-foreground">
                        No stored credentials yet.
                      </TableCell>
                    </TableRow>
                  )}
                  {sortedCredentials.map((item) => (
                    <TableRow key={item.extensionId}>
                      <TableCell className="font-medium">{item.extensionId}</TableCell>
                      <TableCell className="max-w-72 truncate">{item.scopes.join(", ") || "-"}</TableCell>
                      <TableCell>{item.updatedAt}</TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setExtensionId(item.extensionId);
                              setScopesText(item.scopes.join(","));
                              appendLog(`loaded ${item.extensionId} into form`);
                            }}
                          >
                            Load
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => void copySecret(item.extensionSecret, item.extensionId)}
                          >
                            Copy Secret
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => removeStoredCredential(item.extensionId)}
                          >
                            Remove
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <CardTitle>Server Extension Clients</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-80 overflow-auto rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Extension</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Scopes</TableHead>
                    <TableHead>Updated</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {clients.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={5} className="text-muted-foreground">
                        No extension clients on the server.
                      </TableCell>
                    </TableRow>
                  )}
                  {clients.map((client) => (
                    <TableRow key={client.extensionId}>
                      <TableCell className="font-medium">{client.extensionId}</TableCell>
                      <TableCell>
                        <Badge variant={client.enabled ? "default" : "outline"}>
                          {client.enabled ? "enabled" : "disabled"}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-72 truncate">{client.scopes.join(", ") || "-"}</TableCell>
                      <TableCell>{client.updatedAt}</TableCell>
                      <TableCell>
                        <div className="flex justify-end gap-2">
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setExtensionId(client.extensionId);
                              setScopesText(client.scopes.join(","));
                            }}
                          >
                            Load
                          </Button>
                          <Button
                            size="sm"
                            variant="secondary"
                            onClick={() => void rotateSecret(client.extensionId)}
                          >
                            Rotate
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>

        <Card className="xl:col-span-1">
          <CardHeader>
            <CardTitle>Event Log</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-80 space-y-1 overflow-auto rounded-md border p-2 text-xs">
              {log.length === 0 && <div className="text-muted-foreground">No events yet.</div>}
              {log.map((entry, idx) => (
                <div key={`${entry}-${idx}`}>{entry}</div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
