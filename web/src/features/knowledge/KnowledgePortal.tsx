import { FormEvent, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { searchKnowledge } from "@/api/knowledge";

export function KnowledgePortal() {
  const [query, setQuery] = useState("");
  const search = useMutation({ mutationFn: () => searchKnowledge(query.trim()) });

  function submit(event: FormEvent) {
    event.preventDefault();
    if (query.trim().length >= 2) search.mutate();
  }

  return (
    <section className="rounded border border-line bg-canvas-surface">
      <header className="border-b border-line px-3 py-2">
        <h2 className="text-2xs font-mono uppercase tracking-wider text-ink-subtle">Knowledge Portal</h2>
        <p className="mt-1 text-xs text-ink-muted">
          Read-only project documentation search. MCP and A2A peers use the same server-side index.
        </p>
      </header>
      <form onSubmit={submit} className="flex gap-2 border-b border-line p-3">
        <label htmlFor="knowledge-query" className="sr-only">Search documentation</label>
        <input
          id="knowledge-query"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search architecture, approvals, routing…"
          className="min-w-0 flex-1 rounded border border-line bg-canvas-inset px-3 py-2 text-sm text-ink placeholder:text-ink-subtle focus:border-accent focus:outline-none"
        />
        <button
          type="submit"
          disabled={query.trim().length < 2 || search.isPending}
          className="rounded border border-accent bg-accent/10 px-4 text-xs font-semibold text-accent disabled:opacity-40"
        >
          {search.isPending ? "Searching…" : "Search"}
        </button>
      </form>
      <div className="space-y-2 p-3">
        {search.isError && (
          <p className="text-xs text-status-err">
            Search failed. Confirm the Orama portal is reachable on port 8002 and authenticated.
          </p>
        )}
        {search.data?.hits.length === 0 && <p className="text-xs text-ink-muted">No matching documentation.</p>}
        {search.data?.hits.map((hit) => (
          <article key={hit.path} className="rounded border border-line bg-canvas-inset p-3">
            <div className="flex items-baseline justify-between gap-3">
              <h3 className="text-sm font-medium text-ink">{hit.title}</h3>
              <code className="text-2xs text-ink-subtle">{hit.path}</code>
            </div>
            <p className="mt-2 text-xs leading-5 text-ink-muted">{hit.excerpt}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
