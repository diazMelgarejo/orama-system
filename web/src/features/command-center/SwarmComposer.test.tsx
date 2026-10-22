import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SwarmComposer } from "./SwarmComposer";
import { launchSwarm, previewSwarm } from "@/api/swarm";
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

const DEFAULT_OBJECTIVE =
  "Analyze the attached financial report and produce key risk factors, opportunities, and a 1-page executive summary.";

const approvedPreview: SwarmPreview = {
  objective: DEFAULT_OBJECTIVE,
  task_type: "reasoning",
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

  it("disables Launch when composer inputs no longer match the approved preview", () => {
    renderComposer(approvedPreview);
    fireEvent.change(screen.getByPlaceholderText(/describe what the swarm should accomplish/i), {
      target: { value: "A different objective that still has enough characters" },
    });
    expect(screen.getByRole("button", { name: "Launch Swarm" })).toBeDisabled();
    expect(screen.getByText(/inputs changed since the last approval/i)).toBeInTheDocument();
  });

  it("matches the server-normalized objective after preview", () => {
    renderComposer({
      ...approvedPreview,
      objective: "Objective with surrounding whitespace",
    });
    fireEvent.change(screen.getByPlaceholderText(/describe what the swarm should accomplish/i), {
      target: { value: "  Objective with surrounding whitespace  " },
    });

    expect(screen.getByRole("button", { name: "Launch Swarm" })).toBeEnabled();
  });

  it("disables Launch after a successful launch until a new preview arrives", async () => {
    vi.mocked(launchSwarm).mockResolvedValueOnce({
      accepted: true,
      blocked: false,
      session_id: "swarm-test",
      accepted_jobs: [],
      failed_jobs: [],
      preview: {
        objective: DEFAULT_OBJECTIVE,
        task_type: "reasoning",
        optimize_for: "quality",
        preferred_device: "auto",
        assignments: [],
        hardware_policy: { ok: true, violations: [] },
      },
    });
    renderComposer(approvedPreview);
    fireEvent.click(screen.getByRole("button", { name: "Launch Swarm" }));
    await waitFor(() => expect(screen.getByText(/session swarm-test/i)).toBeInTheDocument());
    expect(screen.getByRole("button", { name: "Launch Swarm" })).toBeDisabled();
  });

  it("shows an error badge and orphaned jobs instead of a green session badge", async () => {
    vi.mocked(launchSwarm).mockResolvedValueOnce({
      accepted: false,
      blocked: false,
      launch_blocked: true,
      launch_blocked_reason: "orphaned_jobs_after_rollback",
      session_id: "swarm-orphan",
      accepted_jobs: [],
      failed_jobs: [{ role: "verifier-agent", error: "fail" }],
      cancelled_jobs: [],
      orphaned_jobs: ["job-context-agent"],
      launch_attempt_id: "attempt-1",
      preview: {
        objective: DEFAULT_OBJECTIVE,
        task_type: "reasoning",
        optimize_for: "quality",
        preferred_device: "auto",
        assignments: [],
        hardware_policy: { ok: true, violations: [] },
      },
    });
    renderComposer(approvedPreview);
    fireEvent.click(screen.getByRole("button", { name: "Launch Swarm" }));
    await waitFor(() => expect(screen.getByRole("status", { name: /launch blocked/i })).toBeInTheDocument());
    expect(screen.queryByText(/session swarm-orphan/i)).not.toBeInTheDocument();
    expect(screen.getByText(/orphaned jobs: job-context-agent/i)).toBeInTheDocument();
  });

  it("shows preview errors instead of the Preview-first hint", async () => {
    vi.mocked(previewSwarm).mockRejectedValueOnce(new Error("unreachable"));
    renderComposer();
    fireEvent.click(screen.getByRole("button", { name: "Preview Plan" }));
    await waitFor(() => expect(screen.getByText(/preview failed/i)).toBeInTheDocument());
    expect(screen.queryByText(/run preview first/i)).not.toBeInTheDocument();
  });
});
