import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import App from "./App";

vi.mock("@/api/appState", () => ({
  fetchAppState: vi.fn(() => Promise.reject(new Error("unreachable"))),
}));

vi.mock("@/api/artifacts", () => ({
  listJobArtifacts: vi.fn(() => Promise.resolve({ artifacts: [] })),
}));

function renderApp() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <App />
    </QueryClientProvider>,
  );
}

describe("App", () => {
  it("renders the operator console and shows mock-state fallback on API error", async () => {
    renderApp();
    expect(screen.getByText("Command")).toBeInTheDocument();
    await waitFor(() => {
      expect(
        screen.getByText(/\/api\/app\/state unreachable/i),
      ).toBeInTheDocument();
    });
  });
});
