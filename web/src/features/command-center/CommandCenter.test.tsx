import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CommandCenter } from "./CommandCenter";

vi.mock("@/api/appState", () => ({
  fetchAppState: vi.fn(() => Promise.reject(new Error("unreachable"))),
}));

vi.mock("@/api/artifacts", () => ({
  listJobArtifacts: vi.fn(() => Promise.resolve({ artifacts: [] })),
}));

function renderCommandCenter() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <CommandCenter />
    </QueryClientProvider>,
  );
}

async function waitForConsole() {
  await waitFor(() => {
    expect(screen.getByText("Command")).toBeInTheDocument();
  });
}

function clickNav(label: string) {
  fireEvent.click(screen.getByRole("button", { name: label }));
}

describe("CommandCenter nav smokes", () => {
  it("composer page renders swarm composer without the command dashboard runs table", async () => {
    renderCommandCenter();
    await waitForConsole();
    clickNav("Composer");

    expect(screen.getByText("Swarm Composer")).toBeInTheDocument();
    expect(screen.queryByText("View All Runs")).not.toBeInTheDocument();
    expect(screen.queryByText("PT Runtime")).not.toBeInTheDocument();
  });

  it("runs page renders the runs table without the swarm composer panel", async () => {
    renderCommandCenter();
    await waitForConsole();
    clickNav("Runs");

    expect(screen.getByText("View All Runs")).toBeInTheDocument();
    expect(screen.queryByText("Swarm Composer")).not.toBeInTheDocument();
    expect(screen.queryByText("Launch Swarm")).not.toBeInTheDocument();
  });

  it("artifacts page renders the artifacts panel without the swarm composer panel", async () => {
    renderCommandCenter();
    await waitForConsole();
    clickNav("Artifacts");

    expect(
      screen.getByText(/all artifacts pass through the redaction gateway/i),
    ).toBeInTheDocument();
    expect(screen.queryByText("Swarm Composer")).not.toBeInTheDocument();
    expect(screen.queryByText("Launch Swarm")).not.toBeInTheDocument();
  });
});
