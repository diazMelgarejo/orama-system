# SECURITY

## Credential handling policy
Tracked secret names:
{{secret_names}}

Keychain lookup pattern:
`{{keychain_pattern}}`

Mandatory rules:
- Never print raw secrets to stdout or logs.
- Never commit secrets to git.
- Never embed credentials in source files.
- Read secrets at runtime from approved secret stores.
- Scope credentials to least privilege.
- Rotate keys after suspected exposure.

Runtime controls:
- Validate secret presence before external calls.
- Return structured errors when a secret is missing.
- Redact sensitive tokens in diagnostics.
- Separate operational logs from secret-bearing payloads.

Incident response:
1. Revoke exposed credential.
2. Rotate dependent credentials.
3. Re-run health checks.
4. Document remediation in incident notes.

Compliance note:
When policy and convenience conflict, policy wins.
