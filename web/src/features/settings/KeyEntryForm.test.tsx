import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { KeyEntryForm } from "./KeyEntryForm";
import {
  listSessionSecrets,
  purgeSessionSecrets,
  saveSessionSecrets,
  setSessionSecret,
} from "@/api/sessionSecrets";

vi.mock("@/api/sessionSecrets", () => ({
  listSessionSecrets: vi.fn(),
  purgeSessionSecrets: vi.fn(),
  saveSessionSecrets: vi.fn(),
  setSessionSecret: vi.fn(),
}));

const VALUE = "fixture-value-not-a-real-key";

function renderForm() {
  const client = new QueryClient({
    defaultOptions: { mutations: { retry: false }, queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <KeyEntryForm />
    </QueryClientProvider>,
  );
}

function liveResult() {
  return screen.getByRole("status", { name: "Key entry result" });
}

beforeEach(() => {
  vi.mocked(listSessionSecrets).mockReset().mockResolvedValue({ names: [], status: {} });
  vi.mocked(setSessionSecret).mockReset().mockResolvedValue({ name: "WANDB_API_KEY", state: "set" });
  vi.mocked(saveSessionSecrets).mockReset().mockResolvedValue({ kind: "env", file: ".env" });
  vi.mocked(purgeSessionSecrets).mockReset().mockResolvedValue({ purged: true, names: [] });
});

describe("KeyEntryForm", () => {
  it("uses a password field with autocomplete off", async () => {
    renderForm();

    const field = screen.getByLabelText("Value");
    expect(field).toHaveAttribute("type", "password");
    expect(field).toHaveAttribute("autocomplete", "off");
    await screen.findByText("not set");
  });

  it("sends the value in the request body, clears the field and leaves no value in the page", async () => {
    vi.mocked(listSessionSecrets)
      .mockResolvedValueOnce({ names: [], status: {} })
      .mockResolvedValue({ names: ["WANDB_API_KEY"], status: { WANDB_API_KEY: "set" } });
    renderForm();
    await screen.findByText("not set");

    fireEvent.change(screen.getByLabelText("Value"), { target: { value: VALUE } });
    fireEvent.click(screen.getByRole("button", { name: "Set key" }));

    await waitFor(() => expect(setSessionSecret).toHaveBeenCalledWith("WANDB_API_KEY", VALUE));
    expect(screen.getByLabelText("Value")).toHaveValue("");
    await screen.findByText("set");
    expect(document.body.innerHTML).not.toContain(VALUE);
  });

  it("announces the stored name in a live region", async () => {
    renderForm();
    await screen.findByText("not set");

    fireEvent.change(screen.getByLabelText("Value"), { target: { value: VALUE } });
    fireEvent.click(screen.getByRole("button", { name: "Set key" }));

    expect(liveResult()).toHaveAttribute("aria-live", "polite");
    await waitFor(() => expect(liveResult()).toHaveTextContent("WANDB_API_KEY is set for this session."));
  });

  it("shows set or not set and never a stored value", async () => {
    vi.mocked(listSessionSecrets).mockResolvedValue({
      names: ["WANDB_API_KEY"],
      status: { WANDB_API_KEY: "set" },
    });
    renderForm();

    await screen.findByText("set");
    expect(screen.getByLabelText("Value")).toHaveValue("");
    expect(screen.queryByText(/fixture-value-not-a-real-key/)).not.toBeInTheDocument();
  });

  it("shows not set for a name this session has not stored", async () => {
    renderForm();
    await screen.findByText("not set");

    fireEvent.change(screen.getByLabelText("Name"), { target: { value: "OPENROUTER_API_KEY" } });

    expect(screen.getByText("not set")).toBeInTheDocument();
  });

  it("surfaces a refused value as an alert and clears the secret anyway", async () => {
    vi.mocked(setSessionSecret).mockRejectedValue(new Error("nothing was stored: the value was refused"));
    renderForm();
    await screen.findByText("not set");

    fireEvent.change(screen.getByLabelText("Value"), { target: { value: VALUE } });
    fireEvent.click(screen.getByRole("button", { name: "Set key" }));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/nothing was stored/i));
    expect(screen.getByLabelText("Value")).toHaveValue("");
    expect(document.body.innerHTML).not.toContain(VALUE);
  });

  it("surfaces a listing failure instead of showing a silent empty state", async () => {
    vi.mocked(listSessionSecrets).mockRejectedValue(new Error("401 on /api/session-secrets"));
    renderForm();

    await screen.findByText(/Keys could not be read: 401 on \/api\/session-secrets/);
  });

  it("offers both save targets with plain text and reports the written file", async () => {
    vi.mocked(saveSessionSecrets).mockResolvedValue({ kind: "session-env", file: ".env.abc123def456" });
    renderForm();
    await screen.findByText("not set");

    expect(screen.getByRole("group", { name: "Save targets" })).toBeInTheDocument();
    expect(screen.getByText(".env: written when .env has no filled value")).toBeInTheDocument();
    expect(screen.getByText(".env.<session>: written when .env already has values")).toBeInTheDocument();
    expect(screen.getByText(/An existing \.env is never overwritten/)).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Save to file" }));

    await waitFor(() => expect(liveResult()).toHaveTextContent(".env.abc123def456"));
    expect(liveResult()).toHaveTextContent(/\.env was left untouched/);
  });

  it("purges the session and announces it", async () => {
    renderForm();
    await screen.findByText("not set");

    fireEvent.click(screen.getByRole("button", { name: "Forget keys" }));

    await waitFor(() => expect(purgeSessionSecrets).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(liveResult()).toHaveTextContent(/Cleared every key/i));
  });
});
