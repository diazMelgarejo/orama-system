import { FOOTER_ITEMS, NAV_ITEMS } from "./consoleNavigation";

interface NavLeftProps {
  active?: string;
  onSelect?: (id: string) => void;
}

export function NavLeft({ active = "command", onSelect }: NavLeftProps) {
  return (
    <nav aria-label="Console sections" className="hidden h-full w-44 flex-col border-r border-line bg-canvas-surface md:flex">
      {/* Main nav */}
      <ul className="flex flex-1 flex-col pt-2">
        {NAV_ITEMS.map(({ id, label, Icon }) => {
          const selected = active === id;
          return (
            <li key={id}>
              <button
                type="button"
                aria-current={selected ? "page" : undefined}
                onClick={() => onSelect?.(id)}
                className={`flex w-full items-center gap-2.5 px-3 py-2 text-left text-sm transition-colors ${
                  selected
                    ? "border-l-2 border-accent bg-accent/8 text-accent"
                    : "border-l-2 border-transparent text-ink-muted hover:bg-canvas-raised hover:text-ink"
                }`}
              >
                <Icon />
                <span className={selected ? "font-medium" : ""}>{label}</span>
              </button>
            </li>
          );
        })}
      </ul>

      {/* Footer: settings + docs + version */}
      <div className="border-t border-line">
        {FOOTER_ITEMS.map(({ id, label, Icon }) => (
          <button
            key={id}
            type="button"
            aria-current={active === id ? "page" : undefined}
            onClick={() => onSelect?.(id)}
            className={`flex w-full items-center gap-2.5 px-3 py-2 text-left text-xs transition-colors ${
              active === id
                ? "border-l-2 border-accent bg-accent/8 text-accent"
                : "border-l-2 border-transparent text-ink-subtle hover:text-ink-muted"
            }`}
          >
            <Icon />
            <span>{label}</span>
          </button>
        ))}
        <div className="px-3 py-2 text-2xs font-mono text-ink-subtle">v1.1.1.0</div>
      </div>
    </nav>
  );
}
