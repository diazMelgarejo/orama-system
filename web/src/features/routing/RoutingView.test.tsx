import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { RoutingView } from "./RoutingView";
import { mockState } from "@/data/mockState";
import { LMSTUDIO_WIN_ROW_MODEL } from "./routingState";

describe("RoutingView", () => {
  it("renders the Win LM Studio row when lmstudio_win is online", () => {
    render(<RoutingView state={mockState} />);
    expect(screen.getByText(LMSTUDIO_WIN_ROW_MODEL)).toBeInTheDocument();
  });

  it("hides the Win LM Studio row when lmstudio_win is offline", () => {
    const runtimeData = mockState.runtime.data as Record<string, string>;
    const offline: typeof mockState = {
      ...mockState,
      runtime: {
        ...mockState.runtime,
        data: { ...runtimeData, lmstudio_win: "offline" },
      },
    };
    render(<RoutingView state={offline} />);
    expect(screen.queryByText(LMSTUDIO_WIN_ROW_MODEL)).not.toBeInTheDocument();
  });
});
