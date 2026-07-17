import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  bootstrapNotificationSession,
  openPortalNotificationStream,
} from "@/api/notifications";

const RETRY_DELAYS_MS = [1_000, 2_000, 4_000, 8_000, 30_000] as const;
const TERMINAL_STATUSES = new Set([401, 403, 404]);

function errorStatus(error: unknown): number | undefined {
  if (!error || typeof error !== "object" || !("status" in error)) {
    return undefined;
  }
  const status = (error as { status: unknown }).status;
  return typeof status === "number" ? status : undefined;
}

export function usePortalNotifications(): void {
  const queryClient = useQueryClient();
  const closeStreamRef = useRef<(() => void) | undefined>();
  const retryTimerRef = useRef<ReturnType<typeof setTimeout> | undefined>();
  const retryAttemptRef = useRef(0);
  const connectingRef = useRef(false);
  const abortRef = useRef<AbortController | undefined>();

  useEffect(() => {
    let disposed = false;
    let terminal = false;

    const clearRetryTimer = () => {
      if (retryTimerRef.current !== undefined) {
        clearTimeout(retryTimerRef.current);
        retryTimerRef.current = undefined;
      }
    };

    const scheduleReconnect = () => {
      if (disposed || terminal || connectingRef.current || retryTimerRef.current !== undefined) {
        return;
      }
      const delay = RETRY_DELAYS_MS[Math.min(retryAttemptRef.current, RETRY_DELAYS_MS.length - 1)];
      retryAttemptRef.current += 1;
      retryTimerRef.current = setTimeout(() => {
        retryTimerRef.current = undefined;
        void connect();
      }, delay);
    };

    const connect = async () => {
      if (disposed || terminal || connectingRef.current) {
        return;
      }
      connectingRef.current = true;
      abortRef.current = new AbortController();
      try {
        await bootstrapNotificationSession(abortRef.current.signal);
        if (disposed || terminal) {
          return;
        }
        retryAttemptRef.current = 0;
        closeStreamRef.current = openPortalNotificationStream(
          () => {
            void queryClient.invalidateQueries({ queryKey: ["appState"] });
          },
          scheduleReconnect,
        );
      } catch (error) {
        if (TERMINAL_STATUSES.has(errorStatus(error) ?? 0)) {
          terminal = true;
          return;
        }
        scheduleReconnect();
      } finally {
        connectingRef.current = false;
      }
    };

    void connect();

    return () => {
      disposed = true;
      terminal = true;
      clearRetryTimer();
      abortRef.current?.abort();
      closeStreamRef.current?.();
      closeStreamRef.current = undefined;
    };
  }, [queryClient]);
}
