import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { KnowledgePortal } from "./KnowledgePortal";
import { searchKnowledge } from "@/api/knowledge";

vi.mock("@/api/knowledge", () => ({
  searchKnowledge: vi.fn(),
}));

describe("KnowledgePortal", () => {
  it("lets an end user search documentation", async () => {
    vi.mocked(searchKnowledge).mockResolvedValueOnce({
      query: "approval",
      read_only: true,
      hits: [{ title: "Human Approval", path: "plans/hitl.md", excerpt: "Human approval is required.", score: 7 }],
    });
    render(
      <QueryClientProvider client={new QueryClient()}>
        <KnowledgePortal />
      </QueryClientProvider>,
    );
    fireEvent.change(screen.getByLabelText("Search documentation"), { target: { value: "approval" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    await waitFor(() => expect(screen.getByText("Human Approval")).toBeInTheDocument());
    expect(screen.getByText("plans/hitl.md")).toBeInTheDocument();
    expect(screen.getByLabelText("Search documentation")).toHaveAttribute("maxLength", "200");
  });

  it("does not show stale hits when the input changes before the response arrives", async () => {
    let resolveSearch: (value: Awaited<ReturnType<typeof searchKnowledge>>) => void = () => {};
    vi.mocked(searchKnowledge).mockImplementationOnce(
      () =>
        new Promise((resolve) => {
          resolveSearch = resolve;
        }),
    );
    render(
      <QueryClientProvider client={new QueryClient()}>
        <KnowledgePortal />
      </QueryClientProvider>,
    );
    const input = screen.getByLabelText("Search documentation");
    fireEvent.change(input, { target: { value: "approval" } });
    fireEvent.click(screen.getByRole("button", { name: "Search" }));
    fireEvent.change(input, { target: { value: "routing" } });
    resolveSearch({
      query: "approval",
      read_only: true,
      hits: [{ title: "Human Approval", path: "plans/hitl.md", excerpt: "Human approval is required.", score: 7 }],
    });
    await waitFor(() => expect(searchKnowledge).toHaveBeenCalled());
    expect(screen.queryByText("Human Approval")).not.toBeInTheDocument();
  });
});
