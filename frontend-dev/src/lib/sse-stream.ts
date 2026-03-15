import { getApiBaseUrl } from "@/lib/api";

export type SseEvent = {
  event: string;
  data: string;
};

export type SseStreamOptions = {
  signal?: AbortSignal;
  token?: string | null;
  timeoutMs?: number;
  onEvent?: (event: SseEvent) => void;
};

function resolveApiOrigin(): string {
  const base = getApiBaseUrl();
  if (base.startsWith("http")) {
    return base.replace(/\/api\/?$/, "");
  }
  if (typeof window !== "undefined") {
    return window.location.origin;
  }
  throw new Error("Cannot resolve API origin outside browser");
}

function parseEventBlock(block: string): SseEvent | null {
  const lines = block.split(/\r?\n/);
  let event = "message";
  const dataParts: string[] = [];

  for (const line of lines) {
    if (!line || line.startsWith(":")) {
      continue;
    }
    if (line.startsWith("event:")) {
      event = line.slice("event:".length).trim();
      continue;
    }
    if (line.startsWith("data:")) {
      dataParts.push(line.slice("data:".length).trimStart());
    }
  }

  if (!dataParts.length) {
    return null;
  }

  return { event, data: dataParts.join("\n") };
}

export async function streamSse(
  path: string,
  options: SseStreamOptions = {},
): Promise<void> {
  const controller = new AbortController();
  const timeoutMs = options.timeoutMs ?? 60000;

  const onAbort = () => controller.abort();
  if (options.signal) {
    if (options.signal.aborted) {
      controller.abort();
    } else {
      options.signal.addEventListener("abort", onAbort, { once: true });
    }
  }

  const timeout = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const token = options.token ?? localStorage.getItem("token");
    const headers: Record<string, string> = {
      Accept: "text/event-stream",
      "Cache-Control": "no-cache",
    };
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }
    const response = await fetch(`${resolveApiOrigin()}${path}`, {
      method: "GET",
      headers,
      signal: controller.signal,
    });

    if (!response.ok) {
      throw new Error(`Stream request failed: ${response.status}`);
    }
    if (!response.body) {
      throw new Error("Stream response body is empty");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";
      for (const rawBlock of blocks) {
        const parsed = parseEventBlock(rawBlock);
        if (!parsed) {
          continue;
        }
        options.onEvent?.(parsed);
      }
    }
  } finally {
    clearTimeout(timeout);
    if (options.signal) {
      options.signal.removeEventListener("abort", onAbort);
    }
  }
}
