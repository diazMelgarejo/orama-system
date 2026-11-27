import { execSync } from "node:child_process";
import type { Plugin } from "vite";

type ReadSha = () => string;

const gitSha: ReadSha = () => execSync("git rev-parse HEAD", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim();

/** Stamp every build with the commit it was made from, so the portal can say which build it serves. */
export function buildInfoPlugin(readSha: ReadSha = gitSha, now: () => Date = () => new Date()): Plugin {
  return {
    name: "orama-build-info",
    apply: "build",
    generateBundle() {
      let sha = "unknown";
      try {
        sha = readSha() || "unknown";
      } catch {
        /* not a git checkout: the stamp says "unknown" rather than inventing a commit */
      }
      this.emitFile({
        type: "asset",
        fileName: "build-info.json",
        source: JSON.stringify({ git_sha: sha, built_at: now().toISOString() }) + "\n",
      });
    },
  };
}
