"""Structural rules beyond JSON Schema: filesystem-as-registry checks."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from planscope.validation import validate_tree


@pytest.fixture
def mini_repo(tmp_path: Path, repo_root: Path) -> Path:
    """A copy of the real repository that tests may break freely."""
    root = tmp_path / "planscope"
    shutil.copytree(repo_root / "schemas", root / "schemas")
    shutil.copytree(repo_root / "data", root / "data")
    (root / "config").mkdir()
    shutil.copy(repo_root / "config" / "exchange_rate.yaml", root / "config" / "exchange_rate.yaml")
    return root


def _error_fields(root: Path) -> list[tuple[str, str]]:
    return [(e.file, e.field) for e in validate_tree(root)]


def test_clean_copy_passes(mini_repo: Path) -> None:
    assert validate_tree(mini_repo) == []


def test_provider_directory_without_provider_yaml_fails(mini_repo: Path) -> None:
    (mini_repo / "data" / "providers" / "ghost").mkdir()
    errors = validate_tree(mini_repo)
    assert any(e.field == "provider.yaml" and "ghost" in e.file for e in errors)


def test_provider_id_must_match_directory(mini_repo: Path) -> None:
    path = mini_repo / "data" / "providers" / "openai" / "provider.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("id: openai", "id: not-openai"), encoding="utf-8")
    assert any(e.field == "id" for e in validate_tree(mini_repo))


def test_plan_filename_must_match_id(mini_repo: Path) -> None:
    path = mini_repo / "data" / "providers" / "openai" / "plans" / "example-coding-plan.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("id: example-coding-plan", "id: renamed"), encoding="utf-8")
    assert any(e.field == "id" for e in validate_tree(mini_repo))


def test_plan_provider_must_match_directory(mini_repo: Path) -> None:
    path = mini_repo / "data" / "providers" / "openai" / "plans" / "example-coding-plan.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("provider: openai", "provider: anthropic"), encoding="utf-8")
    assert any(e.field == "provider" for e in validate_tree(mini_repo))


def test_plan_source_ref_must_exist(mini_repo: Path) -> None:
    path = mini_repo / "data" / "providers" / "openai" / "plans" / "example-coding-plan.yaml"
    path.write_text(path.read_text(encoding="utf-8").replace("  - docs", "  - does-not-exist"), encoding="utf-8")
    assert any(e.field == "source_refs" for e in validate_tree(mini_repo))


def test_model_plan_reference_must_exist(mini_repo: Path) -> None:
    path = mini_repo / "data" / "providers" / "openai" / "models.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("plan: example-coding-plan", "plan: ghost-plan"), encoding="utf-8"
    )
    assert any(e.field.endswith(".plan") for e in validate_tree(mini_repo))


def test_unknown_top_level_data_dir_fails(mini_repo: Path) -> None:
    (mini_repo / "data" / "stray").mkdir()
    assert any(e.field == "$" and "未知条目" in e.message for e in validate_tree(mini_repo))


def test_unknown_yaml_in_provider_dir_fails(mini_repo: Path) -> None:
    (mini_repo / "data" / "providers" / "openai" / "stray.yaml").write_text("id: x\n", encoding="utf-8")
    assert any("未知 YAML" in e.message for e in validate_tree(mini_repo))


def test_broken_broken_change_file_reports_file(mini_repo: Path, capsys) -> None:
    from planscope.cli import main

    changes_dir = mini_repo / "data" / "changes" / "2026" / "09"
    (changes_dir / "broken.yaml").write_text("a: [1, 2\n", encoding="utf-8")
    code = main(["--root", str(mini_repo), "validate"])
    captured = capsys.readouterr()
    assert code == 1
    assert "broken.yaml" in captured.err
