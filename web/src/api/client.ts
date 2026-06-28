/**
 * Shared fetch helper for all backend API clients.
 * Vite dev server proxies /api/* to portal_server.py (port 8001).
 * In production, same-origin assumed.
 */

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly url: string,
    public readonly body?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

interface FetchOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
}

export async function apiFetch<T>(path: string, opts: FetchOptions = {}): Promise<T> {
  // No base URL prefix: Vite proxy handles /api/* in dev; production assumes same-origin.
  const url = path;
  const init: RequestInit = {
    method: opts.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      Accept: "application/json",
    },
    signal: opts.signal,
  };
  if (opts.body !== undefined) {
    init.body = JSON.stringify(opts.body);
  }

  const res = await fetch(url, init);
  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      try {
        body = await res.text();
      } catch {
        body = undefined;
      }
    }
    throw new ApiError(
      `${res.status} ${res.statusText} on ${path}`,
      res.status,
      path,
      body,
    );
  }
  return (await res.json()) as T;
}

// oramaclaw conflict resolution types (P2-6)
export interface OramaclawConflict {
  resolution_id: string;
  transaction_id: string;
  created_at: string;
  resolved_at: string | null;
  chosen: string | null;
  conflict: {
    resource_key: string;
    manager: string;
    managed_path: string;
    base_fingerprint: string | null;
    observed_fingerprint: string | null;
    desired_fingerprint: string;
    security_topology: boolean;
    choices: string[];
    resolution_id: string;
  };
}

export interface OramaclawConflictsResponse {
  conflicts: OramaclawConflict[];
}

export interface OramaclawResolveRequest {
  choice: string;
}

export interface OramaclawResolveResponse {
  ok: boolean;
  resolution_id: string;
  chosen: string;
}
