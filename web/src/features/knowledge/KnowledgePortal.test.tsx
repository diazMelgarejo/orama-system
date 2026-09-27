import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { KnowledgePortal } from "./KnowledgePortal";

vi.mock("@/api/knowledge", () => ({
  searchKnowledge: vi.fn(() => Promise.resolve({
    query: "approval",
    read_only: true,
    hits: [{ title: "Human Approval", path: "plans/hitl.md", excerpt: "Human approval is required.", score: 7 }],
  })),
}));

describe("KnowledgePortal", () => {
  it("lets an end user search documentation", async () => {
    render(
      <QueryClientProvider client={new QueryClient()}>
        <KnowledgePortal />
      </QueryClientProvider>,
    );
    fireEvent.change(screen.getByLabelText("Search documentation"), { target: { value: "approval" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => expect(screen.getByText("Human Approval")).toBeInTheDocument());
    expect(screen.getByText("plans/hitl.md")).toBeInTheDocument();
  });
});
