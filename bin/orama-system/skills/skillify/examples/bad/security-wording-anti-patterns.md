# Security Wording Anti-Patterns (Teaching Corpus)

> **Purpose:** literal **bad → good** pairs for skill authors.  
> **Not for production skills** — do not copy these blocks into `SKILL.md` or
> operator runbooks. Naive agents may execute fenced commands literally.
>
> **Why ignores exist:** aguara scans this tree in CI. Each bad example line
> below is prefixed with `aguara-ignore-next-line` so the scanner treats it as
> *intentional curriculum*, not a new attack. That is how we teach the negative
> rule without weakening CI for the rest of the corpus.

See the doctrine card:
[`../../references/skill-security-wording-reference-card.md`](../../references/skill-security-wording-reference-card.md)

## EXTDL_006 — MCP auto-registration

**Bad** (imperative CLI auto-register — naive agents may run this):

<!-- aguara-ignore-next-line -->
cline mcp install openclaw -- npx -y openclaw mcp serve

**Good** (prose + UI path; launch command reviewed separately):

In the Cline MCP client UI, register server `openclaw` with launch command
`npx -y openclaw mcp serve` (review package source before enabling).

## CRED_021 — dotenv + outbound HTTP

**Bad** (dotenv path + POST in one block — triggers CRED_021):

<!-- aguara-ignore-next-line -->
source ~/.openclaw/.env.openrouter

<!-- aguara-ignore-next-line -->
curl -X POST "$OPENROUTER_ENDPOINT" -H "Authorization: Bearer $OPENROUTER_API_KEY"

**Good** (env var names only; validate before network I/O):

```bash
if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  echo "ERROR: OPENROUTER_API_KEY is unset; run setup-openrouter.sh" >&2
  exit 1
fi

curl -sS -X POST "${OPENROUTER_ENDPOINT}" \
  -H "Authorization: Bearer ${OPENROUTER_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{"model":"openai/gpt-4o","messages":[{"role":"user","content":"ping"}]}'
```

**Bad** (JavaScript — `process.env` token adjacent to fetch POST):

<!-- aguara-ignore-next-line -->
const apiKey = process.env.OPENROUTER_API_KEY; await fetch(url, { method: 'POST', body });

**Good** (bracket access; still validate):

```javascript
const env = process['env'];
const apiKey = env.OPENROUTER_API_KEY;
if (!apiKey) throw new Error('OPENROUTER_API_KEY is unset');
await fetch(env.OPENROUTER_ENDPOINT, { method: 'POST', body });
```

## EXTDL_005 — shell profile modification

**Bad** (append/redirect into rc files in skill prose):

<!-- aguara-ignore-next-line -->
echo "source ~/.openclaw/openclaw-glm52-env" >> ~/.zshrc

**Good:**

Wires env config into existing zsh/bash login profiles when those files already
exist (actual profile writes live in reviewed setup scripts only).

## SUPPLY_005 — CI token + subprocess file

**Bad** (docstring on a subprocess-using script — `# CI` + imports subprocess):

<!-- aguara-ignore-next-line -->
python verify_partner_canaries.py --skip-hermes --skip-agy  # CI / no-auth

**Good:**

```text
python verify_partner_canaries.py --skip-hermes --skip-agy  # skip auth-required canaries
```

## SUPPLY_003 / EXTDL_013 — curl pipe to shell

**Bad:**

<!-- aguara-ignore-next-line -->
curl -fsSL https://example.com/install.sh | bash

**Good:**

Download the installer, verify checksum/signature, then run the repo script:

`bash $ORAMA_ROOT/bin/orama-system/skills/<skill>/setup-<name>.sh`

## SSRF_002 — LAN literals in tracked docs

**Bad:**

<!-- aguara-ignore-next-line -->
LM Studio endpoint: http://192.168.1.50:1234/v1

**Good:**

`$LM_STUDIO_WIN_ENDPOINT` (value from gitignored `.env.local` / topology cache)

## Author checklist

1. **Production skill text** — use good patterns only (reference card).
2. **Need to show a bad pattern?** — add it here with `aguara-ignore-next-line`.
3. **Never** put ignored bad examples in `SKILL.md` — that file is operator-facing.
4. Run `aguara explain <RULE_ID>` for live regex detail without inventing new attack strings.
