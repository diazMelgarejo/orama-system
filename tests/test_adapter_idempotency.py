from pathlib import Path
import pytest
import gemini_reconciliation as gr

def test_adapter_idempotency(tmp_path: Path):
    root = tmp_path / "gemini" / "skills"
    archive = tmp_path / "archive" / "batch-1"
    ownership = gr.GeminiOwnership("orama", "adapter", "my-adapter", "some/path/SKILL.md", "none")
    
    # Run first time
    gr.reconcile_gemini(root, archive, {"my-adapter"}, lambda s: ownership)
    
    # Assert exists
    assert (root / "my-adapter" / "SKILL.md").exists()
    
    # Run second time against same archive (should be no-op)
    gr.reconcile_gemini(root, archive, {"my-adapter"}, lambda s: ownership)
