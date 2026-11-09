# Tests

## Run All Tests

```bash
pytest tests/ -v
```

In a Linux container whose PID 1 does not reap orphaned processes, run the
suite through the subreaper launcher instead:

```bash
python scripts/ci/run_with_subreaper.py python -m pytest tests/ -v
```

The launcher reaps orphaned descendants while pytest runs and passes through
pytest's exit code. It does not signal or terminate descendants. Other
platforms run the command without Linux-specific setup.

## Run Specific Suites

```bash
pytest tests/test_single_agent.py -v   # Package integrity + content quality
pytest tests/test_multi_agent.py -v    # Multi-agent structure + config
pytest tests/test_orchestrator.py -v   # Core types + orchestrator logic
```

## Requirements

```bash
pip install pytest
```

No external services needed — all tests use file system and Python stdlib only.

## CI

See `.github/workflows/test.yml` for automated test runs on every push.
