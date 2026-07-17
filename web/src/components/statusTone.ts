import type { StatusTone } from "./StatusBadge";

/** Infer tone from a free-form status string. */
export function statusToTone(status: string | undefined | null): StatusTone {
  if (!status) return "neutral";
  const s = status.toLowerCase();
  if (s.includes("ok") || s.includes("online") || s.includes("ready") || s === "completed" || s === "succeeded") return "ok";
  if (s.includes("warn") || s === "queued" || s === "pending" || s === "waiting") return "warn";
  if (s.includes("err") || s.includes("fail") || s === "blocked" || s === "rejected") return "err";
  if (s === "running" || s === "in_progress" || s === "active") return "info";
  if (s.includes("gpu") || s.includes("busy")) return "gpu";
  return "neutral";
}
