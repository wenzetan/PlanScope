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


_MINIMAL_PLAN = """\
id: {id}
name: {name}
provider: {provider}
type:
  - token_plan
status: unknown
region: {region}
market: {market}
audience: {audience}
checked_at: "2026-09-23T10:30:00+08:00"
"""


def test_variant_plans_coexist_under_one_provider(mini_repo: Path) -> None:
    """同一 Provider 下 region / audience / market 变体必须能作为独立记录共存。

    模拟首批数据的真实形态：小米中国/海外双价格 + 团队版；GLM 国内 BigModel / 海外 Z.ai。
    """
    plans_dir = mini_repo / "data" / "providers" / "openai" / "plans"
    variants = [
        ("token-plan-cn", "Token Plan CN", "cn", "null", "personal"),
        ("token-plan-global", "Token Plan Global", "global", "null", "personal"),
        ("team-token-plan", "Team Token Plan", "cn", "bigmodel", "team"),
        ("legacy-coding-plan", "Legacy Coding Plan", "cn", "null", "personal"),
    ]
    for plan_id, name, region, market, audience in variants:
        content = _MINIMAL_PLAN.format(
            id=plan_id, name=name, provider="openai", region=region, market=market, audience=audience
        )
        if plan_id == "legacy-coding-plan":
            content = content.replace("status: unknown", "status: deprecated")
        (plans_dir / f"{plan_id}.yaml").write_text(content, encoding="utf-8")

    errors = validate_tree(mini_repo)
    assert errors == [], "\n".join(str(e) for e in errors)


def test_variant_ids_need_not_be_globally_unique(mini_repo: Path) -> None:
    """id 只需在同一 Provider 内唯一：不同 Provider 可以有同名 plan id。"""
    other = mini_repo / "data" / "providers" / "anthropic" / "plans"
    other.mkdir(exist_ok=True)
    content = _MINIMAL_PLAN.format(
        id="example-coding-plan",
        name="Example Coding Plan (Template)",
        provider="anthropic",
        region="null",
        market="null",
        audience="null",
    )
    (other / "example-coding-plan.yaml").write_text(content, encoding="utf-8")
    assert validate_tree(mini_repo) == []


def test_anthropic_models_are_rejected_in_models_yaml(mini_repo: Path) -> None:
    """AGENTS.md 绝对规则：永不记录 Anthropic 系模型（无论哪个 Provider）。"""
    path = mini_repo / "data" / "providers" / "openai" / "models.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("model_id: example-model", "model_id: claude-sonnet-4"),
        encoding="utf-8",
    )
    errors = validate_tree(mini_repo)
    assert any(e.field == "models[0].model_id" and "Anthropic" in e.message for e in errors)


def test_anthropic_models_are_rejected_in_plan_models(mini_repo: Path) -> None:
    path = mini_repo / "data" / "providers" / "openai" / "plans" / "example-coding-plan.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace(
            "models: []", "models:\n  - anthropic/claude-haiku-4"
        ),
        encoding="utf-8",
    )
    errors = validate_tree(mini_repo)
    assert any(e.field == "models[0]" and "Anthropic" in e.message for e in errors)


def test_anthropic_models_are_rejected_in_benchmarks(mini_repo: Path) -> None:
    path = mini_repo / "data" / "providers" / "openai" / "benchmarks" / "example-ttft.yaml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("model: example-model", "model: claude-opus-4"),
        encoding="utf-8",
    )
    errors = validate_tree(mini_repo)
    assert any(e.field == "model" and "Anthropic" in e.message for e in errors)


def test_non_anthropic_models_pass_validation(mini_repo: Path) -> None:
    """反向保证：规则只拦截 Anthropic 系，普通模型不受影响。"""
    from planscope.validation import _is_anthropic_model

    assert _is_anthropic_model("claude-sonnet-4")
    assert _is_anthropic_model("Anthropic/claude-3")
    assert _is_anthropic_model("openrouter/claude-haiku")
    assert not _is_anthropic_model("example-model")
    assert not _is_anthropic_model("gpt-5.2")
    assert not _is_anthropic_model("mimo-v2.6-flash")
    assert validate_tree(mini_repo) == []


def test_privacy_records_are_scoped_and_named(mini_repo: Path) -> None:
    """一个 Provider 多份隐私记录（consumer/business…）：id 必须等于文件名。"""
    import shutil

    src = mini_repo / "data" / "providers" / "kimi" / "privacy" / "business.yaml"
    dst_dir = mini_repo / "data" / "providers" / "anthropic" / "privacy"
    dst_dir.mkdir(exist_ok=True)

    # 多份记录按 scope 共存：结构有效
    dst = dst_dir / "business.yaml"
    shutil.copy(src, dst)
    dst.write_text(dst.read_text(encoding="utf-8").replace("provider: kimi", "provider: anthropic"), encoding="utf-8")
    consumer = dst_dir / "consumer.yaml"
    shutil.copy(dst, consumer)
    consumer.write_text(
        consumer.read_text(encoding="utf-8").replace("id: business", "id: consumer"), encoding="utf-8"
    )
    assert validate_tree(mini_repo) == []

    # id 与文件名不一致 → 拒绝
    consumer.write_text(
        consumer.read_text(encoding="utf-8").replace("id: consumer", "id: wrong"), encoding="utf-8"
    )
    errors = validate_tree(mini_repo)
    assert any(e.field == "id" and "consumer.yaml" in e.file for e in errors)

    # 单份记录也仍然有效（provider 不一致会被拒）
    bad = dst_dir / "business.yaml"
    bad.write_text(bad.read_text(encoding="utf-8").replace("provider: anthropic", "provider: kimi"), encoding="utf-8")
    assert any(e.field == "provider" and "business.yaml" in e.file for e in validate_tree(mini_repo))
