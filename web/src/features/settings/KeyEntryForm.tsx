import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError } from "@/api/client";
import {
  listSessionSecrets,
  purgeSessionSecrets,
  saveSessionSecrets,
  setSessionSecret,
} from "@/api/sessionSecrets";

const DEFAULT_NAME = "WANDB_API_KEY";
const LISTING_KEY = ["session-secrets"] as const;

const SAVE_TARGETS = [
  { file: ".env", when: "written when .env has no filled value" },
  { file: ".env.<session>", when: "written when .env already has values" },
];

const FIELD_CLASS =
  "w-full rounded border border-line bg-canvas-inset px-2.5 py-2 text-xs font-mono text-ink focus:border-accent focus:outline-none focus:ring-1 focus:ring-accent";
const BUTTON_CLASS =
  "rounded border border-line bg-canvas-raised px-3 py-1.5 text-xs text-ink transition hover:border-accent hover:text-accent disabled:opacity-40";

function messageFor(error: unknown): string {
  if (error instanceof ApiError) {
    const detail = (error.body as { detail?: unknown } | undefined)?.detail;
    return typeof detail === "string" ? detail : `${error.status} on ${error.url}`;
  }
  return error instanceof Error ? error.message : "the request failed";
}

export function KeyEntryForm() {
  const queryClient = useQueryClient();
  const [name, setName] = useState(DEFAULT_NAME);
  const [value, setValue] = useState("");
  const [result, setResult] = useState("");
  const [error, setError] = useState("");

  const listing = useQuery({ queryKey: LISTING_KEY, queryFn: () => listSessionSecrets() });

  const setMutation = useMutation({
    mutationFn: (input: { name: string; value: string }) => setSessionSecret(input.name, input.value),
    onSuccess: async (saved) => {
      setResult(`${saved.name} is set for this session.`);
      await queryClient.invalidateQueries({ queryKey: LISTING_KEY });
    },
    onError: (cause) => {
      setResult("");
      setError(messageFor(cause));
    },
  });

  const saveMutation = useMutation({
    mutationFn: () => saveSessionSecrets(),
    onSuccess: (saved) => {
      setError("");
      setResult(
        saved.kind === "env"
          ? `Wrote ${saved.file}, the repository file and nothing else.`
          : `Wrote ${saved.file}, a new session file; .env was left untouched.`,
      );
    },
    onError: (cause) => {
      setResult("");
      setError(messageFor(cause));
    },
  });

  const purgeMutation = useMutation({
    mutationFn: () => purgeSessionSecrets(),
    onSuccess: async () => {
      setError("");
      setResult("Cleared every key entered in this session.");
      await queryClient.invalidateQueries({ queryKey: LISTING_KEY });
    },
    onError: (cause) => {
      setResult("");
      setError(messageFor(cause));
    },
  });

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setResult("");
    setError("");
    const submitted = value;
    if (!name.trim()) {
      setError("Enter the key name.");
      return;
    }
    if (!submitted) {
      setError("Enter the key value before submitting.");
      return;
    }
    // Clear the field at submit time: the value must not stay in the page while the request is in flight.
    setValue("");
    setMutation.mutate({ name: name.trim(), value: submitted });
  }

  const names = listing.data?.names ?? [];
  const isSet = names.includes(name.trim());
  const busy = setMutation.isPending || saveMutation.isPending || purgeMutation.isPending;

  return (
    <section aria-labelledby="key-entry-heading" className="mb-4 rounded border border-line bg-canvas-surface">
      <header className="flex items-center justify-between border-b border-line px-3 py-2">
        <h2 id="key-entry-heading" className="text-xs font-mono uppercase tracking-wider text-ink-subtle">
          Session Keys
        </h2>
        <span aria-live="polite" className="text-xs font-mono uppercase tracking-wider text-ink-subtle">
          {isSet ? "set" : "not set"}
        </span>
      </header>

      <form onSubmit={submit} className="space-y-3 p-3">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div>
            <label htmlFor="key-name" className="mb-1 block text-xs uppercase tracking-wider text-ink-subtle">
              Name
            </label>
            <input
              id="key-name"
              type="text"
              value={name}
              onChange={(event) => setName(event.target.value)}
              autoComplete="off"
              spellCheck={false}
              className={FIELD_CLASS}
            />
          </div>
          <div>
            <label htmlFor="key-value" className="mb-1 block text-xs uppercase tracking-wider text-ink-subtle">
              Value
            </label>
            <input
              id="key-value"
              type="password"
              value={value}
              onChange={(event) => setValue(event.target.value)}
              autoComplete="off"
              spellCheck={false}
              className={FIELD_CLASS}
            />
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            type="submit"
            disabled={busy}
            className="rounded border border-accent bg-accent/10 px-4 py-1.5 text-xs font-semibold text-accent transition hover:bg-accent/20 disabled:opacity-40"
          >
            Set key
          </button>
          <button type="button" disabled={busy} onClick={() => saveMutation.mutate()} className={BUTTON_CLASS}>
            Save to file
          </button>
          <button type="button" disabled={busy} onClick={() => purgeMutation.mutate()} className={BUTTON_CLASS}>
            Forget keys
          </button>
          {/* Always mounted so a screen reader announces the result when it appears. */}
          <p
            role="status"
            aria-live="polite"
            aria-label="Key entry result"
            className="ml-auto text-xs text-ink-muted"
          >
            {result}
          </p>
        </div>

        <p role="alert" className="text-xs text-status-err">
          {error}
        </p>

        {listing.isError && (
          <p className="text-xs text-status-err">Keys could not be read: {messageFor(listing.error)}</p>
        )}

        <div
          role="group"
          aria-label="Save targets"
          className="rounded border border-line bg-canvas-inset p-2.5 text-xs text-ink-muted"
        >
          <p className="mb-1 text-ink-subtle">Save writes one plain-text file:</p>
          {SAVE_TARGETS.map((target) => (
            <p key={target.file} className="font-mono">
              {target.file}: {target.when}
            </p>
          ))}
          <p className="mt-1">An existing .env is never overwritten; a new file is refused if it already exists.</p>
        </div>
      </form>
    </section>
  );
}
