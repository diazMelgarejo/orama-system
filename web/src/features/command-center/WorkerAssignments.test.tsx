import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import type { SwarmPreview } from "@/api/swarm";
import { WorkerAssignments } from "./WorkerAssignments";

const preview = (overrides: Partial<SwarmPreview> = {}): SwarmPreview => ({
  objective: "Ship launch",
  task_type: "coding",
  optimize_for: "reliability",
  preferred_device: "auto",
  assignments: [],
  hardware_policy: { ok: true, violations: [] },
  preview_id: "preview-id",
  approval_token: "approval-token",
  strict_mode: true,
  ...overrides,
});

describe("WorkerAssignments", () => {
  it("maps server role names to distinct worker letters", () => {
    render(
      <WorkerAssignments
        preview={preview({
          assignments: [
            "context-agent",
            "architect-agent",
            "executor-agent",
            "verifier-agent",
            "crystallizer-agent",
          ].map((role) => ({
            role,
            specialization: "test",
            intent: "test",
            backend_hint: "lmstudio-mac",
            expected_output_shape: "test",
            verification_rubric: "test",
            routing_source: "pt:/models/route",
          })),
        })}
      />,
    );

    const rows = screen.getAllByRole("row").slice(1);
    expect(rows.map((row) => within(row).getAllByRole("cell")[0].textContent)).toEqual([
      "C",
      "A",
      "E",
      "V",
      "X",
    ]);
  });

  it("renders string policy violations verbatim", () => {
    const violation = "NEVER_MAC bad-model advertised by lmstudio-mac";
    render(
      <WorkerAssignments
        preview={preview({
          hardware_policy: { ok: false, violations: [violation] },
        })}
      />,
    );

    expect(screen.getByText(violation)).toBeInTheDocument();
  });

  it("shows routing failures instead of marking the assignment ready", () => {
    render(
      <WorkerAssignments
        preview={preview({
          assignments: [
            {
              role: "context-agent",
              specialization: "test",
              intent: "test",
              backend_hint: null,
              expected_output_shape: "test",
              verification_rubric: "test",
              routing_source: "portal:fallback",
              routing_error: "ConnectError",
            },
          ],
        })}
      />,
    );

    expect(screen.getByText("Routing failed")).toBeInTheDocument();
    expect(screen.queryByText("Ready")).not.toBeInTheDocument();
    expect(screen.getByText("—")).toBeInTheDocument();
  });
});
