# Gemini Frontmatter Contract

Schema Version: 1

## Official-source evidence
URL: https://gemini.google.com/skills/docs (Placeholder)
Retrieval Date: 2026-08-14
Version: 1.0

## Accepted preserved keys
Exactly `user-invocable`, constrained to the boolean value `false`.

## Rejection rule
An unknown field raises `ValueError("unsupported frontmatter key: <exact-key>")`; a known key with an unaccepted value identifies both the exact key and value in its error.
