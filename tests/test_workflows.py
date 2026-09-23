"""Workflow files must parse as YAML and honor the CI design rules.

There are no scheduled jobs: deployment is push-triggered (``deploy.yml``) or
manual ``workflow_dispatch``; ``validate.yml`` only validates/builds. These
tests lock that in and guard the invalid plain-scalar colon regression.
The trailing test covers ``.github/dependabot.yml`` (not a workflow — it must
not contain a cron deploy, but it must exist so Dependabot pushes update PRs).
"""

from pathlib import Path

import yaml

WORKFLOWS = ("validate.yml", "deploy.yml")


def _load(repo_root: Path, name: str) -> dict:
    path = repo_root / ".github" / "workflows" / name
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{name} 顶层必须是映射"
    return data


def test_all_workflows_parse_as_yaml(repo_root: Path) -> None:
    for name in WORKFLOWS:
        data = _load(repo_root, name)
        assert "jobs" in data, f"{name} 缺少 jobs"


def test_validate_triggers_on_push_and_pr(repo_root: Path) -> None:
    data = _load(repo_root, "validate.yml")
    trigger = data.get("on", data.get(True))
    assert "push" in trigger and "pull_request" in trigger


def test_deploy_triggers_on_push_to_main_and_manual_dispatch(repo_root: Path) -> None:
    """部署只由 push（限路径）或手动 dispatch 触发。"""
    data = _load(repo_root, "deploy.yml")
    trigger = data.get("on", data.get(True))
    assert set(trigger) == {"push", "workflow_dispatch"}, set(trigger)
    assert trigger["push"]["branches"] == ["main"]
    paths = set(trigger["push"]["paths"])
    assert {"data/**", "site/**", "config/**", "schemas/**"} <= paths


def test_no_scheduled_workflows(repo_root: Path) -> None:
    """本项目没有 cron：部署由 push / workflow_dispatch 触发，不自动定时执行。"""
    for path in (repo_root / ".github" / "workflows").glob("*.yml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        trigger = data.get("on", data.get(True)) or {}
        assert "schedule" not in trigger, f"{path.name} 不应有 schedule"


def test_workflows_never_retry(repo_root: Path) -> None:
    """禁止 retry workflow / backoff —— 只扫描实际 YAML 内容，忽略注释。"""
    for name in WORKFLOWS:
        lines = (repo_root / ".github" / "workflows" / name).read_text(encoding="utf-8").splitlines()
        content = "\n".join(line for line in lines if not line.strip().startswith("#")).lower()
        for banned in ("retry:", "backoff", "max-attempt"):
            assert banned not in content, f"{name} 不允许出现: {banned}"


def test_no_colon_inside_plain_run_scalars(repo_root: Path) -> None:
    """run: echo "...X: y..." 这类未加引号的冒号值是非法 YAML —— 逐行扫描防回归。"""
    for name in WORKFLOWS:
        path = repo_root / ".github" / "workflows" / name
        for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            stripped = line.strip()
            if not stripped.startswith("run:"):
                continue
            value = stripped[4:].strip()
            if value.startswith(("|", ">", '"', "'", "{", "[")):
                continue  # 块标量 / 已引用 / flow：内部冒号合法
            assert ": " not in value, (
                f"{name}:{lineno} run 的普通标量中含 ': '（YAML 非法），请改写文案或改用引号: {stripped}"
            )


def test_dependabot_covers_every_dependency_surface(repo_root: Path) -> None:
    """Dependabot 配置必须齐全，否则版本更新 PR 一个都不会推送。

    npm 站点在 site/（不是仓库根），pip 与 github-actions 在仓库根。
    这是 Dependabot "不推送" 的常见原因，锁定防止再被删/漏配。
    """
    path = repo_root / ".github" / "dependabot.yml"
    assert path.is_file(), "缺少 .github/dependabot.yml —— Dependabot 不会推送版本更新 PR"

    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(data, dict) and data.get("version") == 2

    entries = {(u["package-ecosystem"], u["directory"]) for u in data["updates"]}
    assert ("npm", "/site") in entries, "npm 站点在 site/，directory 必须是 /site"
    assert ("pip", "/") in entries
    assert ("github-actions", "/") in entries

    for update in data["updates"]:
        assert update["schedule"]["interval"] == "weekly", "保持低噪：只允许 weekly"
        assert update["open-pull-requests-limit"] >= 1

