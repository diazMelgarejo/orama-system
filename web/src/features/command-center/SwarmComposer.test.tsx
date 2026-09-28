import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SwarmComposer } from "./SwarmComposer";
import { previewSwarm } from "@/api/swarm";
import type { SwarmPreview } from "@/api/swarm";

vi.mock("@/api/swarm", () => ({
  previewSwarm: vi.fn(),
  launchSwarm: vi.fn(),
}));

function renderComposer(previewData?: SwarmPreview) {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <SwarmComposer previewData={previewData} />
    </QueryClientProvider>,
  );
}

const approvedPreview: SwarmPreview = {
  objective: "Ship the knowledge portal",
  task_type: "ops",
  optimize_for: "quality",
  preferred_device: "auto",
  assignments: [],
  hardware_policy: { ok: true, violations: [] },
  preview_id: "preview-1",
  approval_token: "token-1",
  strict_mode: true,
};

describe("SwarmComposer launch gate", () => {
  it("tells the operator to run Preview first when approval credentials are missing", () => {
    renderComposer();
    expect(screen.getByRole("button", { name: "Launch Swarm" })).toBeDisabled();
    expect(screen.getByText(/run preview first to generate an approval token/i)).toBeInTheDocument();
  });

  it("enables Launch only after a real preview id, token, and hardware ok", () => {
    renderComposer(approvedPreview);
    expect(screen.getByRole("button", { name: "Launch Swarm" })).toBeEnabled();
    expect(screen.queryByText(/run preview first/i)).not.toBeInTheDocument();
  });

  it("explains a hardware-blocked preview instead of leaving Launch silently disabled", () => {
    renderComposer({
      ...approvedPreview,
      hardware_policy: { ok: false, violations: [{ reason: "NEVER_MAC" }] },
    });
    expect(screen.getByRole("button", { name: "Launch Swarm" })).toBeDisabled();
    expect(screen.getByText(/hardware policy blocked this preview/i)).toBeInTheDocument();
  });

  it("keeps Context Profile under Advanced as a Phase-5 placeholder", () => {
    renderComposer();
    expect(screen.queryByRole("combobox", { name: /context profile/i })).not.toBeInTheDocument();
    expect(screen.queryByText("Context Profile")).not.toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /advanced options/i }));
    expect(screen.getByText(/context profile/i)).toBeInTheDocument();
    expect(screen.getByText(/coming Phase 5/i)).toBeInTheDocument();
  });

  it("shows preview errors instead of the Preview-first hint", async () => {
    vi.mocked(previewSwarm).mockRejectedValueOnce(new Error("unreachable"));
    renderComposer();
    fireEvent.click(screen.getByRole("button", { name: "Preview Plan" }));
    await waitFor(() => expect(screen.getByText(/preview failed/i)).toBeInTheDocument());
    expect(screen.queryByText(/run preview first/i)).not.toBeInTheDocument();
  });
});
