import type { ReactNode } from "react";
import { EnvBar } from "./EnvBar";
import { NavLeft } from "./NavLeft";
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
      <EnvBar state={state} provenance={provenance} isFetching={isFetching} onNavigate={onNavigate} />
      <div className="flex flex-1 overflow-hidden">
        <NavLeft active={activePage} onSelect={onNavigate} />
        <main className="flex-1 overflow-auto px-4 py-4">{children}</main>
      </div>
    </div>
  );
}
