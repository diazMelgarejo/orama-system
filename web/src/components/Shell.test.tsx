import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { Shell } from "./Shell";
import { UNAVAILABLE_STATE } from "@/features/command-center/dataProvenance";

describe("Shell", () => {
  it("passes provenance to the header so an unavailable API is never shown as healthy", () => {
    render(
      <Shell state={UNAVAILABLE_STATE} provenance={{ kind: "unavailable" }}>
        <p>body</p>
      </Shell>,
    );
    expect(screen.getByText("UNKNOWN")).toBeInTheDocument();
    expect(screen.getByText("body")).toBeInTheDocument();
  });

  it("renders the compact navigation with the active section for narrow screens", () => {
    render(
      <Shell state={UNAVAILABLE_STATE} provenance={{ kind: "unavailable" }} activePage="artifacts">
        <p>body</p>
      </Shell>,
    );
    const compact = screen.getByRole("navigation", { name: "Console sections (compact)" });
    expect(compact).toHaveTextContent("Artifacts");
  });
});
