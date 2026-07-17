import tsParser from "@typescript-eslint/parser";
import tsPlugin from "@typescript-eslint/eslint-plugin";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";

const browserGlobals = {
  AbortSignal: "readonly",
  clearTimeout: "readonly",
  console: "readonly",
  document: "readonly",
  Event: "readonly",
  EventSource: "readonly",
  fetch: "readonly",
  MessageEvent: "readonly",
  React: "readonly",
  RequestInit: "readonly",
  Response: "readonly",
  setTimeout: "readonly",
  window: "readonly",
};

const testGlobals = {
  afterEach: "readonly",
  beforeEach: "readonly",
  describe: "readonly",
  expect: "readonly",
  it: "readonly",
  vi: "readonly",
};

export default [
  {
    ignores: ["dist/**", "node_modules/**", "coverage/**"],
  },
  {
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      parser: tsParser,
      parserOptions: {
        ecmaFeatures: { jsx: true },
        ecmaVersion: "latest",
        sourceType: "module",
      },
      globals: browserGlobals,
    },
    plugins: {
      "@typescript-eslint": tsPlugin,
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "@typescript-eslint/no-unused-vars": [
        "error",
        { argsIgnorePattern: "^_", varsIgnorePattern: "^_" },
      ],
      "no-unused-vars": "off",
      "react-refresh/only-export-components": [
        "error",
        { allowConstantExport: true },
      ],
    },
  },
  {
    files: ["**/*.test.{ts,tsx}", "**/vitest.config.ts"],
    languageOptions: {
      globals: testGlobals,
    },
  },
];
