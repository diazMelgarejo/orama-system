import { apiFetch } from "./client";

/** Names and the word "set" only: the server never returns a value. */
export interface SessionSecretsListing {
  names: string[];
  status: Record<string, "set">;
}

export interface SessionSecretSaved {
  name: string;
  state: "set";
}

/** The two targets the backend can write; it decides which one, and says so. */
export type SessionSaveKind = "env" | "session-env";

export interface SessionSecretsSaveResult {
  kind: SessionSaveKind;
  file: string;
}

export interface SessionSecretsPurgeResult {
  purged: boolean;
  names: string[];
}

export function listSessionSecrets(signal?: AbortSignal): Promise<SessionSecretsListing> {
  return apiFetch<SessionSecretsListing>("/api/session-secrets", { signal });
}

/** The value travels in the body only: never in the path, a query string or a log. */
export function setSessionSecret(
  name: string,
  value: string,
  signal?: AbortSignal,
): Promise<SessionSecretSaved> {
  return apiFetch<SessionSecretSaved>(`/api/session-secrets/${encodeURIComponent(name)}`, {
    method: "PUT",
    body: { value },
    signal,
  });
}

export function saveSessionSecrets(signal?: AbortSignal): Promise<SessionSecretsSaveResult> {
  return apiFetch<SessionSecretsSaveResult>("/api/session-secrets/save", { method: "POST", signal });
}

export function purgeSessionSecrets(signal?: AbortSignal): Promise<SessionSecretsPurgeResult> {
  return apiFetch<SessionSecretsPurgeResult>("/api/session-secrets", { method: "DELETE", signal });
}
