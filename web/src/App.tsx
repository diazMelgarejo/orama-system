import { CommandCenter } from "./features/command-center/CommandCenter";
import { useState } from "react";
import { Workspace } from "./features/workspace/Workspace";
import "./features/workspace/workspace.css";

/** Local workspace with the existing operator console available alongside it. */
export default function App() {
  const [consoleOpen, setConsoleOpen] = useState(false);
  return <>
    <nav className="workspace-navigation" aria-label="Application">
      <span className="workspace-brand">ORAMA <small>/ local workspace</small></span>
      <div><button aria-pressed={!consoleOpen} onClick={() => setConsoleOpen(false)}>Workspace</button><button aria-pressed={consoleOpen} onClick={() => setConsoleOpen(true)}>Operator console</button></div>
    </nav>
    {consoleOpen ? <CommandCenter /> : <Workspace />}
  </>;
}
