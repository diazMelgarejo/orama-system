import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ReadinessStrip } from "./ReadinessStrip";
import { UNAVAILABLE_STATE } from "./dataProvenance";

describe("ReadinessStrip", () => {
  it("stacks the four readiness cards on narrow screens and spreads them on wider ones", () => {
    const { container } = render(<ReadinessStrip state={UNAVAILABLE_STATE} />);
    const grid = container.querySelector(".grid") as HTMLElement;
    expect(grid.className).toMatch(/grid-cols-1/);
    expect(grid.className).toMatch(/sm:grid-cols-2/);
    expect(grid.className).toMatch(/md:grid-cols-4/);
  });

  it("shows all four readiness labels, with an unavailable portal reported as Offline", () => {
    render(<ReadinessStrip state={UNAVAILABLE_STATE} />);
    for (const label of ["PT Runtime", "Portal", "Gateway", "Hardware Policy"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByText("Offline")).toBeInTheDocument();
  });
});
