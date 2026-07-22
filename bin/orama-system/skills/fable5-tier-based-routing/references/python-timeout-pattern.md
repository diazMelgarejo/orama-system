# Python Monitor Until-Loop Timeout Pattern

> Extracted from `fable5-tier-based-routing/SKILL.md`'s Timeout Enforcement
> section during the 2026-07-22 skill-trimming pass. The bash killable-
> background-job pattern in `SKILL.md` covers the same hard invariant (10s
> timeout, no `timeout N && cmd`); this is the Python equivalent for
> callers already in a Python process.

```python
import subprocess
from threading import Thread
import time

def tier_call_with_timeout(tier_endpoint, timeout_secs=10):
    """Call inference endpoint with hard timeout via Monitor pattern."""
    start = time.time()
    proc = subprocess.Popen(
        ["curl", "-X", "POST", tier_endpoint, "--data", "..."],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # Monitor pattern: poll until timeout or completion
    while time.time() - start < timeout_secs:
        retcode = proc.poll()
        if retcode is not None:
            stdout, stderr = proc.communicate()
            return {"result": stdout.decode(), "elapsed": time.time() - start}
        time.sleep(0.1)

    # Timeout: kill process and escalate
    proc.kill()
    proc.wait(timeout=2)  # grace period
    raise TimeoutError(f"Tier call exceeded {timeout_secs}s; escalate to next tier")
```
