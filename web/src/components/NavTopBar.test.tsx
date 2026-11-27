import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";
import { NavTopBar } from "./NavTopBar";

const DESTINATIONS = ["Command", "Composer", "Runs", "Routing", "Artifacts", "Settings", "Docs"];

describe("NavTopBar (compact navigation below 768 px)", () => {
  it("shows the current section and a Sections button that starts closed", () => {
    render(<NavTopBar active="runs" onSelect={() => {}} />);
    expect(screen.getByText("Runs", { selector: "[data-current-section]" })).toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: "Sections" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    expect(screen.queryByRole("list", { name: "Sections" })).not.toBeInTheDocument();
  });

  it("opens the same seven destinations and marks the active one", () => {
    render(<NavTopBar active="routing" onSelect={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "Sections" }));
    const list = screen.getByRole("list", { name: "Sections" });
    const names = within(list).getAllByRole("button").map((b) => b.textContent?.trim());
    expect(names).toEqual(DESTINATIONS);
    expect(within(list).getByRole("button", { name: "Routing" })).toHaveAttribute("aria-current", "page");
    expect(within(list).getByRole("button", { name: "Runs" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("button", { name: "Sections" })).toHaveAttribute("aria-expanded", "true");
  });

  it("selects a destination, closes, and returns focus to the Sections button", () => {
    const onSelect = vi.fn();
    render(<NavTopBar active="command" onSelect={onSelect} />);
    const toggle = screen.getByRole("button", { name: "Sections" });
    fireEvent.click(toggle);
    fireEvent.click(screen.getByRole("button", { name: "Settings" }));
    expect(onSelect).toHaveBeenCalledWith("settings");
    expect(screen.queryByRole("list", { name: "Sections" })).not.toBeInTheDocument();
    expect(toggle).toHaveFocus();
  });

  it("closes on Escape and returns focus to the Sections button", () => {
    render(<NavTopBar active="command" onSelect={() => {}} />);
    const toggle = screen.getByRole("button", { name: "Sections" });
    fireEvent.click(toggle);
    fireEvent.keyDown(screen.getByRole("list", { name: "Sections" }), { key: "Escape" });
    expect(screen.queryByRole("list", { name: "Sections" })).not.toBeInTheDocument();
    expect(toggle).toHaveFocus();
  });

  it("gives every control a touch target of at least 44 px", () => {
    render(<NavTopBar active="command" onSelect={() => {}} />);
    fireEvent.click(screen.getByRole("button", { name: "Sections" }));
    for (const button of screen.getAllByRole("button")) {
      expect(button.className).toMatch(/min-h-11/);
    }
  });

  it("is hidden from desktop widths", () => {
    const { container } = render(<NavTopBar active="command" onSelect={() => {}} />);
    expect(container.firstElementChild?.className).toMatch(/md:hidden/);
  });
});
