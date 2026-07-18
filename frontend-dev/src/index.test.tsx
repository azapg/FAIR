import { cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(cleanup);

vi.mock("@/app/chat/live-page", () => ({
  default: () => <h1>Lazy live chat</h1>,
}));
vi.mock("@/app/chat/page", () => ({
  default: () => <h1>Lazy demo chat</h1>,
}));
vi.mock("@/app/courses/page", () => ({
  default: () => <h1>Lazy courses</h1>,
}));

import { App } from "./index";

describe("App route boundaries", () => {
  it("loads live chat from the canonical chat route", async () => {
    render(<MemoryRouter initialEntries={["/chat"]}><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Lazy live chat" })).toBeInTheDocument();
  });

  it("preserves the live chat compatibility alias", async () => {
    render(<MemoryRouter initialEntries={["/chat/live"]}><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Lazy live chat" })).toBeInTheDocument();
  });

  it("exposes mock chat on the development demo route", async () => {
    render(<MemoryRouter initialEntries={["/chat/demo"]}><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Lazy demo chat" })).toBeInTheDocument();
  });

  it("preserves the courses route", async () => {
    render(<MemoryRouter initialEntries={["/courses"]}><App /></MemoryRouter>);
    expect(await screen.findByRole("heading", { name: "Lazy courses" })).toBeInTheDocument();
  });
});
