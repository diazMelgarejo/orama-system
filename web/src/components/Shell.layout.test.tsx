import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Shell } from "./Shell";
import { UNAVAILABLE_STATE } from "@/features/command-center/dataProvenance";

describe("Shell narrow-screen layout", () => {
  it("keeps the desktop sidebar and adds the compact bar, one of which CSS hides at each width", () => {
    render(
      <Shell state={UNAVAILABLE_STATE} provenance={{ kind: "unavailable" }} activePage="runs">
        <p>body</p>
      </Shell>,
    );
    const desktop = screen.getByRole("navigation", { name: "Console sections" });
    const compact = screen.getByRole("navigation", { name: "Console sections (compact)" });
    expect(desktop.className).toMatch(/hidden/);
    expect(desktop.className).toMatch(/md:flex/);
    expect(compact.parentElement?.className ?? "").toMatch(/md:hidden/);
  });

  it("puts the status row below the compact navigation on narrow screens and lets it wrap", () => {
    const { container } = render(
      <Shell state={UNAVAILABLE_STATE} provenance={{ kind: "unavailable" }}>
        <p>body</p>
      </Shell>,
    );
    const header = container.querySelector("header") as HTMLElement;
    expect(header.className).toMatch(/flex-wrap/);
    expect(header.className).toMatch(/order-2/);
    expect(header.className).toMatch(/md:order-1/);
  });

  it("lets the page body shrink so only data tables scroll sideways", () => {
    render(
      <Shell state={UNAVAILABLE_STATE} provenance={{ kind: "unavailable" }}>
        <p>body</p>
      </Shell>,
    );
    const main = screen.getByRole("main");
    expect(main.className).toMatch(/min-w-0/);
    expect(main.className).toMatch(/overflow-x-hidden/);
  });
});
