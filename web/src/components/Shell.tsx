import type { ReactNode } from "react";
import { EnvBar } from "./EnvBar";
import { NavLeft } from "./NavLeft";
import { NavTopBar } from "./NavTopBar";
import type { AppState } from "@/api/appState";
import type { Provenance } from "@/features/command-center/dataProvenance";

interface ShellProps {
  state: AppState | undefined;
  provenance?: Provenance;
  isFetching?: boolean;
  children: ReactNode;
  activePage?: string;
  onNavigate?: (page: string) => void;
}

export function Shell({ state, provenance, isFetching, children, activePage, onNavigate }: ShellProps) {
  return (
    <div className="flex h-screen flex-col bg-canvas">
      <NavTopBar active={activePage} onSelect={onNavigate} />
      <EnvBar state={state} provenance={provenance} isFetching={isFetching} onNavigate={onNavigate} />
      <div className="order-3 flex min-h-0 flex-1 overflow-hidden">
        <NavLeft active={activePage} onSelect={onNavigate} />
        <main className="min-w-0 flex-1 overflow-y-auto overflow-x-hidden px-3 py-3 md:px-4 md:py-4">{children}</main>
      </div>
    </div>
  );
}
