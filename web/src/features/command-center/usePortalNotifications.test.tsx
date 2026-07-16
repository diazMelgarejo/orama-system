import { act, render } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { usePortalNotifications } from "./usePortalNotifications";
import {
  bootstrapNotificationSession,
  openPortalNotificationStream,
  type PortalNotification,
} from "@/api/notifications";

vi.mock("@/api/notifications", () => ({
  bootstrapNotificationSession: vi.fn(),
  openPortalNotificationStream: vi.fn(),
}));

function HookHarness() {
  usePortalNotifications();
  return null;
}

function renderHookHarness(queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })) {
  const view = render(
    <QueryClientProvider client={queryClient}>
      <HookHarness />
    </QueryClientProvider>,
  );
  return { ...view, queryClient };
}

function notification(): PortalNotification {
  return {
    version: 1,
    event_id: "evt-1",
    type: "job_completed",
    event_type: "job_completed",
    ts: 1784169000,
    source: "orama-portal",
    data: { job_id: "redacted-job" },
    payload: { job_id: "redacted-job" },
  };
}

describe("usePortalNotifications", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.mocked(bootstrapNotificationSession).mockResolvedValue(undefined);
    vi.mocked(openPortalNotificationStream).mockReturnValue(vi.fn());
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.clearAllMocks();
  });

  it("bootstraps the stream and invalidates appState on notifications", async () => {
    const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    const invalidate = vi.spyOn(queryClient, "invalidateQueries");

    renderHookHarness(queryClient);
    await act(async () => {});

    expect(bootstrapNotificationSession).toHaveBeenCalledOnce();
    expect(openPortalNotificationStream).toHaveBeenCalledOnce();

    const [onNotification] = vi.mocked(openPortalNotificationStream).mock.calls[0];
    await act(async () => {
      onNotification(notification());
    });

    expect(invalidate).toHaveBeenCalledWith({ queryKey: ["appState"] });
  });

  it("re-bootstraps with bounded backoff after a disconnect", async () => {
    renderHookHarness();
    await act(async () => {});

    const [, onDisconnect] = vi.mocked(openPortalNotificationStream).mock.calls[0];
    act(() => {
      onDisconnect();
      onDisconnect();
    });

    expect(bootstrapNotificationSession).toHaveBeenCalledTimes(1);
    await act(async () => {
      await vi.advanceTimersByTimeAsync(1_000);
    });

    expect(bootstrapNotificationSession).toHaveBeenCalledTimes(2);
    expect(openPortalNotificationStream).toHaveBeenCalledTimes(2);
  });

  it("does not retry terminal capability failures", async () => {
    vi.mocked(bootstrapNotificationSession).mockRejectedValueOnce({ status: 404 });

    renderHookHarness();
    await act(async () => {});
    await act(async () => {
      await vi.runOnlyPendingTimersAsync();
    });

    expect(bootstrapNotificationSession).toHaveBeenCalledTimes(1);
    expect(openPortalNotificationStream).not.toHaveBeenCalled();
  });

  it("closes the stream and cancels reconnect timers on unmount", async () => {
    const close = vi.fn();
    vi.mocked(openPortalNotificationStream).mockReturnValue(close);

    const { unmount } = renderHookHarness();
    await act(async () => {});

    const [, onDisconnect] = vi.mocked(openPortalNotificationStream).mock.calls[0];
    act(() => {
      onDisconnect();
      unmount();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000);
    });

    expect(close).toHaveBeenCalledOnce();
    expect(bootstrapNotificationSession).toHaveBeenCalledTimes(1);
  });
});
