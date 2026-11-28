import { useRef, useState } from "react";
import type { KeyboardEvent } from "react";

import { FOOTER_ITEMS, NAV_ITEMS } from "./consoleNavigation";

interface NavTopBarProps {
  active?: string;
  onSelect?: (id: string) => void;
}

const DESTINATIONS = [...NAV_ITEMS, ...FOOTER_ITEMS];
const TOUCH_TARGET = "min-h-11";

/**
 * Compact navigation for screens narrower than 768 px: the current section plus a Sections menu with the SAME
 * seven destinations as the desktop sidebar. Closing the menu returns focus to the Sections button.
 */
export function NavTopBar({ active = "command", onSelect }: NavTopBarProps) {
  const [open, setOpen] = useState(false);
  const toggleRef = useRef<HTMLButtonElement>(null);
  const current = DESTINATIONS.find((item) => item.id === active) ?? DESTINATIONS[0];

  function close() {
    setOpen(false);
    toggleRef.current?.focus();
  }

  function choose(id: string) {
    onSelect?.(id);
    close();
  }

  function onKeyDown(event: KeyboardEvent<HTMLUListElement>) {
    if (event.key === "Escape") {
      event.stopPropagation();
      close();
    }
  }

  return (
    <div className="order-1 border-b border-line bg-canvas-surface md:hidden">
      <nav aria-label="Console sections (compact)" className="flex items-center gap-3 px-3">
        <span className="font-mono text-sm font-bold tracking-tight text-accent">orama</span>
        <span data-current-section className="min-w-0 flex-1 truncate text-sm font-medium text-ink">
          {current.label}
        </span>
        <button
          ref={toggleRef}
          type="button"
          aria-expanded={open}
          aria-controls="compact-sections-menu"
          onClick={() => setOpen((value) => !value)}
          className={`${TOUCH_TARGET} rounded border border-line px-3 text-sm text-ink hover:border-accent hover:text-accent focus:outline focus:outline-2 focus:outline-accent`}
        >
          Sections
        </button>
      </nav>
      {open && (
        <ul id="compact-sections-menu" aria-label="Sections" onKeyDown={onKeyDown} className="border-t border-line py-1">
          {DESTINATIONS.map(({ id, label, Icon }) => {
            const selected = id === active;
            return (
              <li key={id}>
                <button
                  type="button"
                  aria-current={selected ? "page" : undefined}
                  onClick={() => choose(id)}
                  className={`${TOUCH_TARGET} flex w-full items-center gap-3 border-l-2 px-3 text-left text-sm focus:outline focus:outline-2 focus:outline-accent ${
                    selected ? "border-accent bg-accent/10 text-accent" : "border-transparent text-ink-muted hover:bg-canvas-raised hover:text-ink"
                  }`}
                >
                  <Icon />
                  <span className={selected ? "font-medium" : ""}>{label}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
