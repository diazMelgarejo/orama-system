import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { EnvBar } from "./EnvBar";
import { mockState } from "@/data/mockState";
import { UNAVAILABLE_STATE } from "@/features/command-center/dataProvenance";

describe("EnvBar provenance", () => {
  it("shows live environment and health only for live data", () => {
    render(<EnvBar state={mockState} provenance={{ kind: "live" }} />);
    expect(screen.getByText("PRODUCTION")).toBeInTheDocument();
    expect(screen.getByText("Healthy")).toBeInTheDocument();
  });

  it("shows UNKNOWN and Unavailable, never PRODUCTION or Healthy, when the API did not answer", () => {
    render(<EnvBar state={UNAVAILABLE_STATE} provenance={{ kind: "unavailable" }} />);
    expect(screen.getByText("UNKNOWN")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.queryByText("PRODUCTION")).not.toBeInTheDocument();
    expect(screen.queryByText("Healthy")).not.toBeInTheDocument();
  });

  it("labels fixtures as DEMO DATA and never as Healthy", () => {
    render(<EnvBar state={mockState} provenance={{ kind: "demo" }} />);
    expect(screen.getByText("DEMO DATA")).toBeInTheDocument();
    expect(screen.queryByText("Healthy")).not.toBeInTheDocument();
  });

  it("labels stale data with a text badge", () => {
    render(<EnvBar state={mockState} provenance={{ kind: "stale", lastGoodAt: 0 }} />);
    expect(screen.getByText("STALE")).toBeInTheDocument();
  });

  it("fails closed: with no provenance it never claims PRODUCTION or Healthy", () => {
    render(<EnvBar state={mockState} />);
    expect(screen.getByText("UNKNOWN")).toBeInTheDocument();
    expect(screen.queryByText("PRODUCTION")).not.toBeInTheDocument();
    expect(screen.queryByText("Healthy")).not.toBeInTheDocument();
  });

  it("says Loading, not Unavailable, before the first answer", () => {
    render(<EnvBar state={UNAVAILABLE_STATE} provenance={{ kind: "loading" }} />);
    expect(screen.getByText("Loading")).toBeInTheDocument();
    expect(screen.queryByText("Unavailable")).not.toBeInTheDocument();
  });

  it("wraps on narrow screens and sits below the compact navigation there", () => {
    const { container } = render(<EnvBar state={mockState} provenance={{ kind: "live" }} />);
    const header = container.querySelector("header") as HTMLElement;
    expect(header.className).toMatch(/flex-wrap/);
    expect(header.className).toMatch(/order-2/);
    expect(header.className).toMatch(/md:order-1/);
  });

  it("hides its own brand on narrow screens, where the compact bar already shows it", () => {
    const { container } = render(<EnvBar state={mockState} provenance={{ kind: "live" }} />);
    const brand = container.querySelector("[data-env-brand]") as HTMLElement;
    expect(brand.className).toMatch(/hidden/);
    expect(brand.className).toMatch(/md:flex/);
  });
});
