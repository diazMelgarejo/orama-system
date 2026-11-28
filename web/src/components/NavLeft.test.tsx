import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { NavLeft } from "./NavLeft";

const DESTINATIONS = ["Command", "Composer", "Runs", "Routing", "Artifacts", "Settings", "Docs"];

describe("NavLeft (desktop sidebar)", () => {
  it("is hidden below 768 px and shown from 768 px up", () => {
    render(<NavLeft active="command" />);
    const nav = screen.getByRole("navigation", { name: "Console sections" });
    expect(nav.className).toMatch(/hidden/);
    expect(nav.className).toMatch(/md:flex/);
  });

  it("offers the same seven destinations as the compact menu and reports selection", () => {
    const onSelect = vi.fn();
    render(<NavLeft active="runs" onSelect={onSelect} />);
    const nav = screen.getByRole("navigation", { name: "Console sections" });
    const names = within(nav).getAllByRole("button").map((b) => b.textContent?.trim());
    expect(names).toEqual(DESTINATIONS);
    fireEvent.click(within(nav).getByRole("button", { name: "Docs" }));
    expect(onSelect).toHaveBeenCalledWith("docs");
  });

  it("marks only the active destination with aria-current", () => {
    render(<NavLeft active="routing" />);
    const nav = screen.getByRole("navigation", { name: "Console sections" });
    expect(within(nav).getByRole("button", { name: "Routing" })).toHaveAttribute("aria-current", "page");
    expect(within(nav).getByRole("button", { name: "Runs" })).not.toHaveAttribute("aria-current");
  });
});
