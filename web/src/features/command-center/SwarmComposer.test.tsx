import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SwarmComposer } from "./SwarmComposer";
import type { SwarmPreview } from "@/api/swarm";

vi.mock("@/api/swarm", () => ({
  previewSwarm: vi.fn(),
  launchSwarm: vi.fn(),
}));

function renderComposer(previewData?: SwarmPreview) {
  return render(
    <QueryClientProvider client={new QueryClient()}>
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
});
