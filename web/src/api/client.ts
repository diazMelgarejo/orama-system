/**
 * Shared fetch helper for all backend API clients.
 * Vite dev server proxies /api/* to portal_server.py (port 8002).
 * In production, same-origin assumed and the HTML shell has the control-plane
 * token injected server-side for loopback requests. In Vite dev mode that
 * injection never happens (Vite serves its own index.html, not portal_server's
 * templated one) -- most /api/* routes are NOT in portal_requires_auth()'s
 * loopback exemption list, so dev calls need a token from somewhere. Set
 * VITE_PORTAL_TOKEN in web/.env.local (gitignored) to attach one; matches
 * whatever ORAMA_CONTROL_PLANE_TOKEN the backend is actually running with.
 */
const DEV_PORTAL_TOKEN = import.meta.env.VITE_PORTAL_TOKEN as string | undefined;

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
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    Accept: "application/json",
  };
  if (DEV_PORTAL_TOKEN) {
    headers.Authorization = `Bearer ${DEV_PORTAL_TOKEN}`;
  }
  const init: RequestInit = {
    method: opts.method ?? "GET",
    headers,
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
  if (res.status === 204) {
    return undefined as T;
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
