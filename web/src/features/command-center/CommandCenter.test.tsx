import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { CommandCenter } from "./CommandCenter";

vi.mock("@/api/appState", () => ({
  fetchAppState: vi.fn(() => Promise.reject(new Error("unreachable"))),
}));

vi.mock("@/api/sessionSecrets", () => ({
  listSessionSecrets: vi.fn(() => Promise.resolve({ names: [], status: {} })),
}));

vi.mock("@/api/artifacts", () => ({
  listJobArtifacts: vi.fn(() => Promise.resolve({ artifacts: [] })),
}));

vi.mock("./usePortalNotifications", () => ({
  usePortalNotifications: vi.fn(),
}));

import { usePortalNotifications } from "./usePortalNotifications";

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
    expect(screen.getByRole("navigation", { name: "Console sections" })).toBeInTheDocument();
  });
}

function clickNav(label: string) {
  fireEvent.click(screen.getByRole("button", { name: label }));
}

describe("CommandCenter nav smokes", () => {
  it("enables portal notification-driven appState refreshes", async () => {
    renderCommandCenter();
    await waitForConsole();

    expect(usePortalNotifications).toHaveBeenCalledOnce();
  });

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

  it("docs page renders the knowledge portal instead of the swarm composer", async () => {
    renderCommandCenter();
    await waitForConsole();
    fireEvent.click(within(screen.getByRole("navigation", { name: "Console sections" })).getByRole("button", { name: "Docs" }));

    expect(screen.getByText("Knowledge Portal")).toBeInTheDocument();
    expect(screen.getByLabelText("Search documentation")).toBeInTheDocument();
    expect(screen.queryByText("Swarm Composer")).not.toBeInTheDocument();
  });

  it("tells the operator to check portal port 8002 when app state is unreachable", async () => {
    renderCommandCenter();
    await waitFor(() => {
      expect(screen.getByText(/portal_server\.py is running on port 8002/i)).toBeInTheDocument();
    });
  });

  it("never shows invented production data when the API is unreachable", async () => {
    renderCommandCenter();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/live data unavailable/i);
    });
    expect(screen.queryByText("PRODUCTION")).not.toBeInTheDocument();
    expect(screen.queryByText("Healthy")).not.toBeInTheDocument();
    expect(screen.queryByText(/run_01JY/)).not.toBeInTheDocument();
    expect(screen.queryByText("us-east-1")).not.toBeInTheDocument();
  });

  it("suppresses the effect controls while live data is unavailable and says why", async () => {
    renderCommandCenter();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/live data unavailable/i);
    });
    expect(screen.getByRole("button", { name: "Launch Swarm" })).toBeDisabled();
    expect(screen.getByRole("button", { name: /preview plan/i })).toBeDisabled();
    expect(screen.getAllByText(/controls are off until live data returns/i).length).toBeGreaterThan(0);
  });
});

describe("CommandCenter demo mode", () => {
  afterEach(() => vi.unstubAllEnvs());

  it("labels the fixtures as a demo, and keeps every effect control inert", async () => {
    vi.stubEnv("VITE_PORTAL_DEMO", "1");
    renderCommandCenter();
    await waitFor(() => {
      expect(screen.getAllByText(/demo data/i).length).toBeGreaterThan(0);
    });
    expect(screen.getByRole("button", { name: "Launch Swarm" })).toBeDisabled();
    expect(screen.getByRole("button", { name: /preview plan/i })).toBeDisabled();
  });
});

describe("CommandCenter live data", () => {
  it("shows live environment and an enabled composer only when the API answered", async () => {
    const { fetchAppState } = await import("@/api/appState");
    const { mockState } = await import("@/data/mockState");
    vi.mocked(fetchAppState).mockResolvedValueOnce(mockState);
    renderCommandCenter();
    await waitFor(() => {
      expect(screen.getByText("PRODUCTION")).toBeInTheDocument();
    });
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("does not show a preview from before live data was lost", async () => {
    renderCommandCenter();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(/live data unavailable/i);
    });
    expect(screen.queryByText(/preview-/i)).not.toBeInTheDocument();
  });
});

describe("CommandCenter settings page", () => {
  it("opens the write-only session key form from the Settings entry", async () => {
    renderCommandCenter();
    await waitForConsole();
    clickNav("Settings");
    expect(screen.getByRole("heading", { name: "Session Keys" })).toBeInTheDocument();
    expect(screen.queryByText("Swarm Composer")).not.toBeInTheDocument();
  });
});
