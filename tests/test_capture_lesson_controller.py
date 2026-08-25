"""TDD contract for the forward-compatible lesson-capture controller."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "bin" / "orama-system" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def _payload(controller):
    return controller.LessonPayload(
        pattern="Verification Skipped",
        what_went_wrong="A branch was published without inspecting its final file scope.",
        root_cause="The local patch was mistaken for the final repository tree.",
        prevention_rule="Inspect the final outgoing range before publication.",
        verification_trigger="Does the final tree preserve every intended path?",
        applied_to="Git publication",
        good_example="Review name-status before updating a ref.",
        bad_example="Publish a partial tree from memory.",
    )


def test_development_mode_delegates_to_pt_agent_stack(tmp_path: Path, monkeypatch) -> None:
    import lesson_controller as controller

    pt_root = tmp_path / "Perpetua-Tools"
    learn = pt_root / ".agent" / "tools" / "learn.py"
    learn.parent.mkdir(parents=True)
    learn.write_text("# fixture\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(argv, **_kwargs):
        calls.append([str(arg) for arg in argv])
        return subprocess.CompletedProcess(argv, 0, stdout="graduated\n", stderr="")

    monkeypatch.setattr(controller.subprocess, "run", fake_run)
    backend = controller.resolve_backend(
        mode="development", backend_name="pt-agent", pt_root=pt_root
    )

    backend.capture(_payload(controller))

    assert calls and calls[0][:2] == [sys.executable, str(learn)]
    assert "--rationale" in calls[0]
    assert "Verification Skipped:" in calls[0][2]


def test_runtime_mode_fails_closed_until_anamnesis_is_provisioned() -> None:
    import lesson_controller as controller

    backend = controller.resolve_backend(mode="runtime", backend_name="auto", pt_root=None)

    with pytest.raises(controller.LessonBackendUnavailable) as excinfo:
        backend.capture(_payload(controller))

    assert excinfo.value.code == "ORAMASYS_LESSON_E_ANAMNESIS_UNAVAILABLE"


def test_legacy_backend_remains_an_explicit_compatibility_escape_hatch(tmp_path: Path) -> None:
    import lesson_controller as controller

    target = tmp_path / "tasks" / "lessons.md"
    backend = controller.resolve_backend(
        mode="development", backend_name="legacy", pt_root=None, legacy_path=target
    )

    backend.capture(_payload(controller))

    content = target.read_text(encoding="utf-8")
    assert "# Lessons Learned" in content
    assert "Verification Skipped" in content


def test_legacy_task_log_migrates_to_home_without_creating_new_task_log(
    tmp_path: Path,
) -> None:
    import capture_lesson

    project = tmp_path / "project"
    source = project / "tasks" / "lessons.md"
    source.parent.mkdir(parents=True)
    source.write_text("legacy lesson\n", encoding="utf-8")
    home = tmp_path / "home"
    home.mkdir()

    destination = capture_lesson.find_lessons_file(project, home_dir=home)

    assert destination == home / "lessons.md"
    assert destination.read_text(encoding="utf-8") == "legacy lesson\n"
    assert not source.exists()


def test_legacy_default_is_home_level_and_does_not_create_missing_task_log(
    tmp_path: Path,
) -> None:
    import capture_lesson

    home = tmp_path / "home"
    home.mkdir()

    destination = capture_lesson.find_lessons_file(tmp_path / "project", home_dir=home)

    assert destination == home / "lessons.md"
    assert not destination.exists()


def test_task_plan_does_not_create_a_legacy_lesson_log(tmp_path: Path) -> None:
    project = tmp_path / "project"
    task_plan = ROOT / "bin" / "orama-system" / "scripts" / "create_task_plan.sh"

    subprocess.run(
        ["bash", str(task_plan), "Controller migration", "--dir", str(project)],
        check=True,
        capture_output=True,
        text=True,
    )

    assert (project / "tasks" / "todo.md").exists()
    assert not (project / "tasks" / "lessons.md").exists()


def test_auto_development_requires_pt_instead_of_silently_fragmenting_memory() -> None:
    import lesson_controller as controller

    with pytest.raises(controller.LessonBackendUnavailable) as excinfo:
        controller.resolve_backend(mode="development", backend_name="auto", pt_root=None)

    assert excinfo.value.code == "ORAMASYS_LESSON_E_PT_AGENT_UNAVAILABLE"


def test_quick_capture_collects_only_a_rule_and_delegates(monkeypatch) -> None:
    import capture_lesson
    import lesson_controller as controller

    captured = []
    answers = iter(["Always inspect final name-status before publication."])

    class Backend:
        def capture(self, payload) -> None:
            captured.append(payload)

    monkeypatch.setattr(capture_lesson, "prompt", lambda *_args, **_kwargs: next(answers))

    capture_lesson.capture_interactive(
        "Verification Skipped", Backend(), quick=True
    )

    assert len(captured) == 1
    assert isinstance(captured[0], controller.LessonPayload)
    assert captured[0].prevention_rule.startswith("Always inspect")


@pytest.mark.parametrize("action", ["--review", "--stats"])
def test_runtime_review_and_stats_fail_closed(action: str, monkeypatch) -> None:
    import capture_lesson

    monkeypatch.setattr(capture_lesson.sys, "argv", ["capture_lesson.py", "--mode", "runtime", action])

    with pytest.raises(SystemExit) as excinfo:
        capture_lesson.main()

    assert excinfo.value.code == 3
