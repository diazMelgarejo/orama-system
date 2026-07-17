import { apiFetch } from "./client";

export const portalNotificationTypes = [
  "agent_state_changed",
  "fleet_topology_changed",
  "hardware_status_changed",
  "job_completed",
  "phase_transition",
] as const;

export type PortalNotificationType = (typeof portalNotificationTypes)[number];

export interface PortalNotification {
  version: 1;
  event_id: string;
  type: PortalNotificationType;
  event_type: PortalNotificationType;
  ts: number;
  source: "orama-portal";
  data: Record<string, unknown>;
  payload: Record<string, unknown>;
}

export async function bootstrapNotificationSession(signal?: AbortSignal): Promise<void> {
  await apiFetch<void>("/api/notifications/session", { method: "POST", signal });
}

export function openPortalNotificationStream(
  onNotification: (notification: PortalNotification) => void,
  onDisconnect: () => void,
): () => void {
  const source = new EventSource("/api/notifications/stream", { withCredentials: true });
  let closed = false;

  const closeAndReport = () => {
    if (closed) {
      return;
    }
    closed = true;
    source.close();
    onDisconnect();
  };

  for (const type of portalNotificationTypes) {
    source.addEventListener(type, (event) => {
      if (closed) {
        return;
      }
      try {
        onNotification(JSON.parse((event as MessageEvent<string>).data) as PortalNotification);
      } catch {
        closeAndReport();
      }
    });
  }
  source.addEventListener("error", closeAndReport);

  return () => {
    if (closed) {
      return;
    }
    closed = true;
    source.close();
  };
}
