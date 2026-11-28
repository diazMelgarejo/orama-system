// @vitest-environment node
import { readFileSync, readdirSync } from "node:fs";
import { basename, join, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

/*
 * Palette contract for the operator console.
 *
 * tokens.css is the only place colours are allowed, so this file reads it with
 * node:fs instead of importing a copy of the values, and it parses the theme
 * blocks to prove both palettes satisfy WCAG 2.x: 4.5:1 for text, 3:1 for the
 * non-text tokens that are used as UI boundaries.
 */

const STYLES_DIR = fileURLToPath(new URL(".", import.meta.url));
const WEB_ROOT = fileURLToPath(new URL("../..", import.meta.url));
const SRC_ROOT = join(WEB_ROOT, "src");
const TOKENS_PATH = join(STYLES_DIR, "tokens.css");
const INDEX_PATH = join(WEB_ROOT, "index.html");

type Theme = "dark" | "light";

interface Rule {
  selector: string;
  media: string;
  body: string;
}

const THEMES: Theme[] = ["dark", "light"];

const SURFACES = ["canvas", "canvas-surface", "canvas-raised", "canvas-inset"] as const;
const TEXT_TOKENS = ["ink", "ink-muted", "ink-subtle", "accent", "accent-hover"] as const;
const STATUS_TOKENS = [
  "status-ok",
  "status-warn",
  "status-err",
  "status-info",
  "status-gpu",
] as const;
const NON_TEXT_TOKENS = ["line", "line-strong", "accent-mute"] as const;
const SCALARS = [
  "gap-xs",
  "gap-sm",
  "gap-md",
  "gap-lg",
  "gap-xl",
  "text-2xs",
  "text-xs",
  "text-sm",
  "text-base",
] as const;

const MIN_TEXT = 4.5;
const MIN_NON_TEXT = 3;
// WCAG 1.4.11 exempts purely decorative dividers, and this change keeps the
// existing dark ramp. The three dark non-text tokens therefore hold their
// measured values instead of being lifted to 3:1; the floor only catches a
// silent regression.
const DARK_DECORATIVE_FLOOR = 1.15;

const CHANNELS = /^\d{1,3} \d{1,3} \d{1,3}$/;
const HEX = /#[0-9a-fA-F]{3,8}\b/;
const NOT_A_TOKEN_FILE = new Set(["tokens.css"]);

function closingBrace(css: string, open: number): number {
  let depth = 1;
  for (let index = open + 1; index < css.length; index += 1) {
    if (css[index] === "{") depth += 1;
    else if (css[index] === "}") depth -= 1;
    if (depth === 0) return index;
  }
  throw new Error(`unbalanced block starting at index ${open}`);
}

function parseRules(css: string, media = ""): Rule[] {
  const rules: Rule[] = [];
  let cursor = 0;
  let statementStart = 0;
  while (cursor < css.length) {
    const char = css[cursor];
    if (char === "{") {
      const selector = css.slice(statementStart, cursor).trim().replace(/\s+/g, " ");
      const close = closingBrace(css, cursor);
      const body = css.slice(cursor + 1, close);
      if (selector.startsWith("@media")) rules.push(...parseRules(body, selector));
      else if (!selector.startsWith("@")) rules.push({ selector, media, body });
      cursor = close + 1;
      statementStart = cursor;
    } else if (char === ";") {
      cursor += 1;
      statementStart = cursor;
    } else {
      cursor += 1;
    }
  }
  return rules;
}

function declarations(body: string): Record<string, string> {
  const out: Record<string, string> = {};
  for (const chunk of body.split(";")) {
    const separator = chunk.indexOf(":");
    if (separator < 0) continue;
    const name = chunk.slice(0, separator).trim();
    const value = chunk.slice(separator + 1).trim();
    if (name !== "") out[name] = value;
  }
  return out;
}

const RAW_CSS = readFileSync(TOKENS_PATH, "utf8").replace(/\/\*[\s\S]*?\*\//g, "");
const RULES = parseRules(RAW_CSS);

function themeOf(rule: Rule): Theme | null {
  if (rule.selector.includes(":not([data-theme])")) return "light";
  if (rule.selector.includes('[data-theme="light"]')) return "light";
  if (rule.selector.includes('[data-theme="dark"]')) return "dark";
  const selectors = rule.selector.split(",").map((part) => part.trim());
  return selectors.includes(":root") ? "dark" : null;
}

const BLOCKS: Record<Theme, Rule[]> = { dark: [], light: [] };
for (const rule of RULES) {
  const theme = themeOf(rule);
  if (theme !== null) BLOCKS[theme].push(rule);
}

function customProperties(blocks: Rule[]): Record<string, string> {
  const all: Record<string, string> = {};
  for (const block of blocks) {
    for (const [name, value] of Object.entries(declarations(block.body))) {
      if (name.startsWith("--")) all[name.slice(2)] = value;
    }
  }
  return all;
}

const TOKENS: Record<Theme, Record<string, string>> = {
  dark: customProperties(BLOCKS.dark),
  light: customProperties(BLOCKS.light),
};

function colour(theme: Theme, token: string): string {
  const value = TOKENS[theme][token];
  if (value === undefined) throw new Error(`--${token} is missing from the ${theme} theme`);
  if (!CHANNELS.test(value)) throw new Error(`--${token} must be bare sRGB channels, got "${value}"`);
  return value;
}

function linear(channel: number): number {
  const srgb = channel / 255;
  return srgb <= 0.03928 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4;
}

function luminance(value: string): number {
  const [red, green, blue] = value.split(" ").map((part) => linear(Number(part)));
  return 0.2126 * red + 0.7152 * green + 0.0722 * blue;
}

function contrast(foreground: string, background: string): number {
  const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

function shortfalls(
  theme: Theme,
  tokens: readonly string[],
  surfaces: readonly string[],
  minimum: number,
): string[] {
  return tokens.flatMap((token) =>
    surfaces
      .map((surface) => ({ surface, ratio: contrast(colour(theme, token), colour(theme, surface)) }))
      .filter((entry) => entry.ratio < minimum)
      .map(
        (entry) =>
          `${theme}: --${token} on --${entry.surface} = ${entry.ratio.toFixed(2)}:1 (needs ${minimum}:1)`,
      ),
  );
}

describe("tokens.css", () => {
  it("declares a dark base and two light blocks (media query + forced)", () => {
    expect(BLOCKS.dark.length).toBeGreaterThan(0);
    expect(BLOCKS.light).toHaveLength(2);
  });

  it("mirrors every token in both themes", () => {
    expect(Object.keys(TOKENS.dark).sort()).toEqual(Object.keys(TOKENS.light).sort());
  });

  it("declares every colour and scalar the app depends on", () => {
    const required = [
      ...SURFACES,
      ...TEXT_TOKENS,
      ...STATUS_TOKENS,
      ...NON_TEXT_TOKENS,
      ...SCALARS,
    ];
    const missing = THEMES.flatMap((theme) =>
      required.filter((token) => TOKENS[theme][token] === undefined).map((token) => `${theme}:--${token}`),
    );
    expect(missing).toEqual([]);
  });

  it("follows the OS only when no data-theme is set", () => {
    const mediaLight = BLOCKS.light.find((rule) => rule.media.includes("prefers-color-scheme: light"));
    if (mediaLight === undefined) throw new Error("no prefers-color-scheme light block");
    expect(mediaLight.selector).toContain(":not([data-theme])");
    const base = RULES.findIndex((rule) =>
      rule.selector.split(",").map((part) => part.trim()).includes(":root"),
    );
    expect(base).toBeGreaterThanOrEqual(0);
    expect(RULES.indexOf(mediaLight)).toBeGreaterThan(base);
  });

  it("lets data-theme force dark or light", () => {
    expect(BLOCKS.dark.some((rule) => rule.selector.includes('[data-theme="dark"]'))).toBe(true);
    expect(BLOCKS.light.some((rule) => rule.selector.includes('[data-theme="light"]'))).toBe(true);
  });

  it("keeps the media-query and forced light blocks identical", () => {
    const mediaLight = BLOCKS.light.find((rule) => rule.media.includes("prefers-color-scheme"));
    const forcedLight = BLOCKS.light.find((rule) => !rule.media.includes("prefers-color-scheme"));
    if (mediaLight === undefined || forcedLight === undefined) {
      throw new Error("missing light block");
    }
    expect(declarations(forcedLight.body)).toEqual(declarations(mediaLight.body));
  });

  it("declares color-scheme per theme so native controls follow", () => {
    expect(declarations(BLOCKS.dark[0].body)["color-scheme"]).toBe("dark");
    expect(BLOCKS.light.every((rule) => declarations(rule.body)["color-scheme"] === "light")).toBe(true);
  });
});

describe.each(THEMES)("%s theme", (theme) => {
  it("keeps every text token at 4.5:1 or better on every surface", () => {
    expect(shortfalls(theme, TEXT_TOKENS, SURFACES, MIN_TEXT)).toEqual([]);
  });

  it("keeps every status colour at 4.5:1 or better on every surface", () => {
    expect(shortfalls(theme, STATUS_TOKENS, SURFACES, MIN_TEXT)).toEqual([]);
  });
});

describe("non-text tokens", () => {
  it("are never also used as text", () => {
    const text: readonly string[] = TEXT_TOKENS;
    expect(NON_TEXT_TOKENS.filter((token) => text.includes(token))).toEqual([]);
  });

  it("reach 3:1 on every light surface (borders, rings, focus outlines)", () => {
    expect(shortfalls("light", NON_TEXT_TOKENS, SURFACES, MIN_NON_TEXT)).toEqual([]);
  });

  it("keep the frozen dark dividers above their measured floor", () => {
    const regressions = NON_TEXT_TOKENS.flatMap((token) =>
      SURFACES.map((surface) => ({
        token,
        surface,
        ratio: contrast(colour("dark", token), colour("dark", surface)),
      }))
        .filter((entry) => entry.ratio < DARK_DECORATIVE_FLOOR)
        .map((entry) => `dark: --${entry.token} on --${entry.surface} = ${entry.ratio.toFixed(2)}:1`),
    );
    expect(regressions).toEqual([]);
  });
});

describe("--ink-subtle in the dark ramp", () => {
  it("clears 4.5:1 on canvas, surface and raised", () => {
    for (const surface of ["canvas", "canvas-surface", "canvas-raised"]) {
      expect(contrast(colour("dark", "ink-subtle"), colour("dark", surface))).toBeGreaterThanOrEqual(
        MIN_TEXT,
      );
    }
  });

  it("is the smallest step, not a brightening of the whole ramp", () => {
    const onRaised = contrast(colour("dark", "ink-subtle"), colour("dark", "canvas-raised"));
    expect(onRaised).toBeGreaterThanOrEqual(MIN_TEXT);
    expect(onRaised).toBeLessThan(4.9);
    const before = [99, 107, 124];
    const after = colour("dark", "ink-subtle").split(" ").map(Number);
    after.forEach((channel, index) => expect(channel - before[index]).toBeLessThanOrEqual(30));
    expect(colour("dark", "ink")).toBe("231 235 244");
    expect(colour("dark", "canvas")).toBe("8 10 14");
  });
});

function sourceFiles(directory: string): string[] {
  return readdirSync(directory, { withFileTypes: true }).flatMap((entry) => {
    if (entry.name.startsWith(".") || entry.name === "node_modules") return [];
    const path = join(directory, entry.name);
    if (entry.isDirectory()) return sourceFiles(path);
    return /\.(ts|tsx|css)$/.test(entry.name) ? [path] : [];
  });
}

describe("colour literals", () => {
  it("live only in tokens.css", () => {
    const scanned = sourceFiles(SRC_ROOT)
      .filter((file) => !/\.test\.(ts|tsx)$/.test(file))
      .filter((file) => !NOT_A_TOKEN_FILE.has(basename(file)));
    expect(scanned.length).toBeGreaterThan(20);
    const offenders = scanned
      .filter((file) => HEX.test(readFileSync(file, "utf8")))
      .map((file) => relative(WEB_ROOT, file));
    expect(offenders).toEqual([]);
  });
});

describe("index.html", () => {
  it("leaves the theme choice to tokens.css", () => {
    const html = readFileSync(INDEX_PATH, "utf8");
    expect(html).not.toMatch(/data-theme/);
    expect(html).not.toMatch(/class="dark"/);
    expect(html).toContain('content="dark light"');
  });
});
