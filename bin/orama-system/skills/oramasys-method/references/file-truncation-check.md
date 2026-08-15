# File Truncation Check

After every whole-file write and before commit, re-read the file from the
write target. Compare its line count with the expected complete content and
inspect its final structural lines.

For remote write tools, fetch one exact commit before commit and inspect that
single response for both checks:

```bash
tmp=$(mktemp)
trap 'rm -f "$tmp"' EXIT
curl --fail --location --silent --show-error \
  "https://raw.githubusercontent.com/<org>/<repo>/<commit-sha>/<path>" \
  >"$tmp"
wc -l "$tmp"
tail -5 "$tmp"
```

If the result is unexpectedly short or structurally incomplete, do not commit.
Re-read the full original, reconstruct the complete file, and repeat the
verification.
