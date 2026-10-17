import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "@/api/client";
import { Workspace } from "./Workspace";

vi.mock("@/api/client", () => ({ apiFetch: vi.fn() }));

const result = {
  run_id: "run-fixture", status: "verified", privacy: "local", execution: "offline-deterministic",
  csv: "claim,source_id,source_title,quote\n", artifact_sha256: "abc", receipt_sha256: "def",
  receipt_json: '{"canonical":"receipt bytes"}\n', artifact_name: "evidence.csv",
  receipt: { schema_version: "1", task: "Create a cited CSV", privacy: "local", execution: "offline-deterministic", created_at: "2026-10-16", sources: [], checks: [{ name: "exact extraction", passed: true }], limitations: ["Does not establish factual truth."], artifact_sha256: "abc", row_count: 1 },
};

describe("Workspace", () => {
  beforeEach(() => vi.clearAllMocks());
  afterEach(() => { vi.restoreAllMocks(); vi.useRealTimers(); });

  it("runs an editable source through the authenticated API with local privacy", async () => {
    vi.mocked(apiFetch).mockResolvedValue(result);
    render(<Workspace />);
    fireEvent.change(screen.getByLabelText("Source passage"), { target: { value: "The fixture has three rows." } });
    fireEvent.click(screen.getByRole("button", { name: "Create verified CSV" }));
    await waitFor(() => expect(screen.getByText("Artifact ready")).toBeInTheDocument());
    expect(apiFetch).toHaveBeenCalledWith("/api/workspace/run", expect.objectContaining({
      method: "POST", body: expect.objectContaining({ privacy: "local", records: [{ claim: "The fixture has three rows.", quote: "The fixture has three rows.", source_id: "source-1" }] }),
    }));
    expect(screen.getByRole("button", { name: "Download CSV" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Research" }));
    expect(screen.getByText("exact extraction")).toBeInTheDocument();
    expect(screen.getByText("Does not establish factual truth.")).toBeInTheDocument();
  });

  it("shows backend errors without claiming an artifact was created", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("Source validation failed"));
    render(<Workspace />);
    fireEvent.click(screen.getByRole("button", { name: "Create verified CSV" }));
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Source validation failed"));
    expect(screen.queryByText("Artifact ready")).not.toBeInTheDocument();
  });

  it("explains progressive privacy without suggesting external execution is available", () => {
    render(<Workspace />);
    fireEvent.change(screen.getByLabelText("Privacy"), { target: { value: "open" } });
    expect(screen.getByText(/Explicitly allow full task sharing/)).toBeInTheDocument();
    expect(screen.getByText(/No model used. No external requests./)).toBeInTheDocument();
  });

  it("downloads exact receipt bytes and releases the generated URL", async () => {
    vi.mocked(apiFetch).mockResolvedValue(result);
    const createObjectURL = vi.fn((_blob: Blob) => "blob:test");
    const revokeObjectURL = vi.fn();
    Object.defineProperty(URL, "createObjectURL", { configurable: true, value: createObjectURL });
    Object.defineProperty(URL, "revokeObjectURL", { configurable: true, value: revokeObjectURL });
    const click = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    render(<Workspace />);
    fireEvent.click(screen.getByRole("button", { name: "Create verified CSV" }));
    await screen.findByText("Artifact ready");
    fireEvent.click(screen.getByRole("button", { name: "Download receipt" }));
    expect(click).toHaveBeenCalledOnce();
    const blob = createObjectURL.mock.calls[0][0] as Blob;
    const bytes = await new Promise<string>(resolve => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result as string);
      reader.readAsText(blob);
    });
    expect(bytes).toBe(result.receipt_json);
    await waitFor(() => expect(revokeObjectURL).toHaveBeenCalledWith("blob:test"), { timeout: 1500 });
  });
});
