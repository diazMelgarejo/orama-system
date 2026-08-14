# File Truncation Check

After every whole-file write and before commit, re-read the file from the
write target. Compare its line count with the expected complete content and
inspect its final structural lines.

For remote write tools, fetch the exact ref before commit:

```bash
curl -s https://raw.githubusercontent.com/<org>/<repo>/<branch>/<path> | wc -l
curl -s https://raw.githubusercontent.com/<org>/<repo>/<branch>/<path> | tail -5
```

If the result is unexpectedly short or structurally incomplete, do not commit.
Re-read the full original, reconstruct the complete file, and repeat the
verification.
