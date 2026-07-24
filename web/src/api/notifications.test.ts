import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "./client";
import {
  bootstrapNotificationSession,
  openPortalNotificationStream,
  type PortalNotification,
  portalNotificationTypes,
} from "./notifications";

vi.mock("./client", () => ({
  apiFetch: vi.fn(),
}));

class FakeEventSource {
  static instances: FakeEventSource[] = [];

  readonly listeners = new Map<string, Array<(event: MessageEvent<string>) => void>>();
  readonly errorListeners: Array<() => void> = [];
  closed = false;

  constructor(
    readonly url: string,
    readonly options?: EventSourceInit,
  ) {
    FakeEventSource.instances.push(this);
  }

  addEventListener(type: string, listener: EventListenerOrEventListenerObject): void {
    if (type === "error") {
      this.errorListeners.push(() => {
        if (typeof listener === "function") {
          listener(new Event("error"));
        } else {
          listener.handleEvent(new Event("error"));
        }
      });
      return;
    }
    const eventListener = (event: MessageEvent<string>) => {
      if (typeof listener === "function") {
        listener(event);
      } else {
        listener.handleEvent(event);
      }
    };
    this.listeners.set(type, [...(this.listeners.get(type) ?? []), eventListener]);
  }

  dispatch(type: string, data: unknown): void {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(new MessageEvent(type, { data: JSON.stringify(data) }));
    }
  }

  dispatchRaw(type: string, data: string): void {
    for (const listener of this.listeners.get(type) ?? []) {
      listener(new MessageEvent(type, { data }));
    }
  }

  dispatchError(): void {
    for (const listener of this.errorListeners) {
      listener();
    }
  }

  close(): void {
    this.closed = true;
  }
}

describe("portal notifications API", () => {
  beforeEach(() => {
    FakeEventSource.instances = [];
    vi.stubGlobal("EventSource", FakeEventSource);
    vi.mocked(apiFetch).mockResolvedValue(undefined);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  it("bootstraps the same-origin notification session with the shared API helper", async () => {
    const controller = new AbortController();

    await bootstrapNotificationSession(controller.signal);

    expect(apiFetch).toHaveBeenCalledWith("/api/notifications/session", {
      method: "POST",
      signal: controller.signal,
    });
  });

  it("opens a credentialed same-origin EventSource and parses named events", () => {
    const onNotification = vi.fn();
    const onDisconnect = vi.fn();

    const close = openPortalNotificationStream(onNotification, onDisconnect);
    const fake = FakeEventSource.instances[0];

    expect(fake.url).toBe("/api/notifications/stream");
    expect(fake.options).toEqual({ withCredentials: true });
    for (const type of portalNotificationTypes) {
      expect(fake.listeners.has(type)).toBe(true);
    }

    const notification: PortalNotification = {
      version: 1,
      event_id: "evt-1",
      type: "job_completed",
      event_type: "job_completed",
      ts: 1784169000,
      source: "orama-portal",
      data: { job_id: "redacted-job" },
      payload: { job_id: "redacted-job" },
    };
    fake.dispatch("job_completed", notification);

    expect(onNotification).toHaveBeenCalledWith(notification);
    expect(onDisconnect).not.toHaveBeenCalled();
    close();
    expect(fake.closed).toBe(true);
  });

  it("closes and reports disconnect once on malformed JSON", () => {
    const onNotification = vi.fn();
    const onDisconnect = vi.fn();

    openPortalNotificationStream(onNotification, onDisconnect);
    const fake = FakeEventSource.instances[0];

    fake.dispatchRaw("job_completed", "{not-json");
    fake.dispatchRaw("job_completed", "{not-json");

    expect(onNotification).not.toHaveBeenCalled();
    expect(fake.closed).toBe(true);
    expect(onDisconnect).toHaveBeenCalledTimes(1);
  });

  it("closes and reports disconnect once on stream errors", () => {
    const onNotification = vi.fn();
    const onDisconnect = vi.fn();

    openPortalNotificationStream(onNotification, onDisconnect);
    const fake = FakeEventSource.instances[0];

    fake.dispatchError();
    fake.dispatchError();

    expect(onNotification).not.toHaveBeenCalled();
    expect(fake.closed).toBe(true);
    expect(onDisconnect).toHaveBeenCalledTimes(1);
  });
});
