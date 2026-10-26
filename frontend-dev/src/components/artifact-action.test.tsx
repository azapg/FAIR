import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import type { AxiosAdapter } from "axios";

import api from "@/lib/api";
import * as apiModule from "@/lib/api";
import { ArtifactAction } from "@/components/artifact-action";

vi.mock("@/components/pdf-preview", () => ({ PdfPreview: () => null }));
vi.mock("@/components/markdown-renderer", () => ({ MarkdownRenderer: () => null }));

const originalAdapter = api.defaults.adapter;
const originalBaseURL = api.defaults.baseURL;

afterEach(() => {
  cleanup();
  api.defaults.adapter = originalAdapter;
  api.defaults.baseURL = originalBaseURL;
  vi.restoreAllMocks();
});

describe("ArtifactAction", () => {
  it.each(["/api", "http://localhost:8000/api"])(
    "opens protected local content with API base %s",
    async (baseURL) => {
      // Exercise real Axios URL combination, which prefixes root-relative URLs
      // with baseURL. Production uses /api; development uses an absolute base.
      api.defaults.baseURL = baseURL;
      vi.spyOn(apiModule, "getApiBaseUrl").mockReturnValue(baseURL);
      const requests: string[] = [];
      const contentPath = "/api/v1/artifact-storage/local/test/answer.txt";
      const adapter: AxiosAdapter = async (config) => {
        const url = api.getUri(config);
        requests.push(url);
        const download = url.endsWith("/v1/artifacts/test/download");
        return {
          config, status: 200, statusText: "OK", headers: {},
          data: download ? { url: contentPath } : "Private answer opened",
        };
      };
      api.defaults.adapter = adapter;
      render(<ArtifactAction artifact={{ id: "test", title: "answer.txt", mime: "text/plain" }} />);
      fireEvent.click(screen.getByRole("button", { name: "answer.txt" }));

      expect(await screen.findByRole("dialog")).toHaveTextContent("Private answer opened");
      expect(requests).toEqual([
        `${baseURL}/v1/artifacts/test/download`,
        `${new URL(baseURL, window.location.origin).origin}${contentPath}`,
      ]);
    },
  );
});
