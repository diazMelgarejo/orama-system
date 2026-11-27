import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { StatusPill } from "./StatusPill";
import type { StatusPillState } from "./StatusPill";
import type { StatusTone } from "./StatusBadge";

interface Expected {
  readonly label: string;
  readonly tone: StatusTone;
}

/**
 * Hand-written expectations. Record<StatusPillState, ...> fails typecheck when a
 * state is added or renamed without updating the tests.
 */
const EXPECTED: Record<StatusPillState, Expected> = {
  success: { label: "Success", tone: "ok" },
  failed: { label: "Failed", tone: "err" },
  partial: { label: "Partial", tone: "warn" },
  waiting: { label: "Waiting", tone: "warn" },
  waiting_authority: { label: "Waiting for authority", tone: "warn" },
  queued: { label: "Queued", tone: "warn" },
  running: { label: "Running", tone: "info" },
  unknown: { label: "Unknown", tone: "neutral" },
  neutral: { label: "Neutral", tone: "neutral" },
};

const CASES = Object.entries(EXPECTED) as [StatusPillState, Expected][];
const STATES = CASES.map(([state]) => state);

describe("StatusPill", () => {
  it.each(CASES)("renders the state with an inline svg icon and its text label", (state, expected) => {
    const { container } = render(<StatusPill state={state} />);
    const pill = (document.querySelector("[data-state]") as HTMLElement);

    expect(pill).toHaveAttribute("data-state", state);
    expect(pill.textContent?.trim()).toBe(expected.label);

    const icon = container.querySelector("svg");
    expect(icon).not.toBeNull();
    expect(icon?.getAttribute("aria-hidden")).toBe("true");
    expect(icon?.getAttribute("data-icon")).toBe(state);
  });

  it.each(CASES)("takes its tone from statusToTone", (state, expected) => {
    render(<StatusPill state={state} />);

    expect((document.querySelector("[data-state]") as HTMLElement).getAttribute("data-tone")).toBe(expected.tone);
  });

  it.each(CASES)("shows the label as visible text, so the name is never colour or icon only", (state, expected) => {
    render(<StatusPill state={state} />);
    const pill = screen.getByText(expected.label).closest("[data-state]") as HTMLElement;

    expect(pill).not.toHaveAttribute("role", "status"); // a table of pills must not be a table of live regions
    expect(pill.textContent?.trim()).toBe(expected.label);
  });

  it("keeps states that share a tone distinguishable by icon and text", () => {
    const { container } = render(
      <div>
        {STATES.map((state) => (
          <StatusPill key={state} state={state} />
        ))}
      </div>,
    );

    const geometry = Array.from(container.querySelectorAll("svg")).map((icon) => icon.innerHTML);
    expect(geometry).toHaveLength(STATES.length);
    expect(new Set(geometry).size).toBe(STATES.length);

    const rendered = new Map<StatusPillState, { geometry: string; label: string }>();
    for (const state of STATES) {
      const pill = screen.getByText(EXPECTED[state].label).closest("[data-state]") as HTMLElement;
      rendered.set(state, {
        geometry: pill.querySelector("svg")?.innerHTML ?? "",
        label: pill.textContent?.trim() ?? "",
      });
    }

    const tones = new Set(STATES.map((state) => EXPECTED[state].tone));
    for (const tone of tones) {
      const group = STATES.filter((state) => EXPECTED[state].tone === tone);
      if (group.length < 2) continue;

      const icons = new Set(group.map((state) => rendered.get(state)?.geometry));
      const labels = new Set(group.map((state) => rendered.get(state)?.label));
      expect(icons.size).toBe(group.length);
      expect(labels.size).toBe(group.length);
    }
  });

  it("names the shared amber group explicitly", () => {
    render(
      <div>
        <StatusPill state="waiting" />
        <StatusPill state="waiting_authority" />
        <StatusPill state="queued" />
        <StatusPill state="partial" />
      </div>,
    );

    const waiting = screen.getByText("Waiting").closest("[data-state]") as HTMLElement;
    const authority = screen.getByText("Waiting for authority").closest("[data-state]") as HTMLElement;
    const queued = screen.getByText("Queued").closest("[data-state]") as HTMLElement;

    expect(waiting.getAttribute("data-tone")).toBe("warn");
    expect(authority.getAttribute("data-tone")).toBe("warn");
    expect(queued.getAttribute("data-tone")).toBe("warn");
    expect(waiting.querySelector("svg")?.innerHTML).not.toBe(
      authority.querySelector("svg")?.innerHTML,
    );
    expect(queued.querySelector("svg")?.innerHTML).not.toBe(
      waiting.querySelector("svg")?.innerHTML,
    );
  });

  it("renders both sizes at 0.75rem or larger using token classes only", () => {
    for (const size of ["sm", "md"] as const) {
      const { container } = render(<StatusPill state="failed" size={size} />);
      const pill = container.querySelector("[data-state]");
      const classes = pill?.getAttribute("class") ?? "";

      expect(classes).not.toContain("text-2xs");
      expect(classes).toMatch(size === "sm" ? /\btext-xs\b/ : /\btext-sm\b/);
      expect(classes).not.toMatch(/#[0-9a-fA-F]{3,8}/);
      expect(classes).not.toMatch(/\brgba?\(/);
      expect(pill?.getAttribute("style")).toBeNull();
    }
  });

  it("defaults to the small size", () => {
    render(<StatusPill state="running" />);

    expect((document.querySelector("[data-state]") as HTMLElement)).toHaveClass("text-xs");
  });

  it("appends caller classes and keeps the tone styling", () => {
    render(<StatusPill state="success" className="animate-pulse" />);
    const pill = (document.querySelector("[data-state]") as HTMLElement);

    expect(pill).toHaveClass("animate-pulse");
    expect(pill).toHaveClass("bg-status-ok/15");
    expect(pill).toHaveClass("text-status-ok");
  });
});
