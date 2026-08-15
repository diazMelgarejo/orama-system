# Gemini Frontmatter Contract

Schema Version: 1

## Official-source evidence

> **UNVERIFIED — must be filled in before any live reconciliation.** The URL below
> has not been confirmed against Gemini's published documentation. It is recorded
> here as an explicit gap rather than an implied citation, because the P2-1 gate
> requirement is a *reproducible* contract: two runs must be able to validate
> against the same stated source. Treat every "accepted key" below as provisional
> until a real source replaces this block.

- Candidate URL: `https://gemini.google.com/skills/docs` (**placeholder, unconfirmed**)
- Retrieval date: not yet retrieved
- Documented version: not yet established

## Accepted preserved keys

Exactly `user-invocable`, constrained to the boolean value `false`.

## Rejection rule

An unknown field raises `ValueError("unsupported frontmatter key: <exact-key>")`; a
known key with an unaccepted value identifies both the exact key and value in its
error.
