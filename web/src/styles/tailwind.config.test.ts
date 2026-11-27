import postcss from "postcss";
import tailwindcss from "tailwindcss";
import { describe, expect, it } from "vitest";
import config from "../../tailwind.config";

/*
 * The light theme only works because Tailwind stopped holding literal colours
 * and started holding rgb(var(--token) / <alpha-value>) references. These tests
 * fail if a colour name is lost, if a literal sneaks back in, or if an opacity
 * modifier such as bg-status-err/5 stops resolving.
 */

type ColourTree = { [name: string]: string | ColourTree };

const ALPHA_SAFE = /^rgb\(var\(--[a-z-]+\) \/ <alpha-value>\)$/;

const EXPECTED_NAMES = [
  "canvas",
  "canvas-surface",
  "canvas-raised",
  "canvas-inset",
  "line",
  "line-strong",
  "ink",
  "ink-muted",
  "ink-subtle",
  "status-ok",
  "status-warn",
  "status-err",
  "status-info",
  "status-gpu",
  "accent",
  "accent-hover",
  "accent-mute",
];

const colours = config.theme?.extend?.colors as unknown as ColourTree;

function flatten(tree: ColourTree, prefix = ""): Array<[string, string]> {
  return Object.entries(tree).flatMap(([key, value]) => {
    const name = prefix === "" ? key : key === "DEFAULT" ? prefix : `${prefix}-${key}`;
    return typeof value === "string" ? [[name, value] as [string, string]] : flatten(value, name);
  });
}

async function compile(classes: string): Promise<string> {
  const result = await postcss([
    tailwindcss({
      ...config,
      content: [{ raw: `<div class="${classes}"></div>`, extension: "html" }],
    }),
  ]).process("@tailwind utilities;", { from: undefined });
  return result.css;
}

describe("tailwind.config", () => {
  it("keeps every colour name and points it at a CSS variable", () => {
    const entries = flatten(colours);
    expect(entries.map(([name]) => name)).toEqual(EXPECTED_NAMES);
    expect(entries.filter(([, value]) => !ALPHA_SAFE.test(value))).toEqual([]);
  });

  it("still emits working alpha modifiers such as bg-status-err/5", async () => {
    const css = await compile(
      "bg-status-err/5 border-status-err/40 bg-canvas-raised/50 text-status-err",
    );
    expect(css).toMatch(/background-color: rgb\(var\(--status-err\)\s*\/\s*0?\.05\)/);
    expect(css).toMatch(/border-color: rgb\(var\(--status-err\)\s*\/\s*0?\.4\)/);
    expect(css).toMatch(/background-color: rgb\(var\(--canvas-raised\)\s*\/\s*0?\.5\)/);
    expect(css).toMatch(/color: rgb\(var\(--status-err\) \/ (?:1|var\(--tw-text-opacity, 1\))\)/);
  });
});
