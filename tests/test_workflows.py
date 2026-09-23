"""Workflow files must parse as YAML and honor the CI design rules.

daily-refresh.yml once shipped an unquoted ``run: echo "Phase 2: ..."`` —
a colon+space inside a plain scalar is invalid YAML, GitHub could not parse
the file, and the schedule would silently never fire (a 0-job placeholder
failed run was created on push instead). These tests prevent that class of
regression and lock in the trigger discipline.
"""

from pathlib import Path

import yaml

WORKFLOWS = ("validate.yml", "daily-refresh.yml")


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


def test_daily_refresh_has_exactly_one_schedule_and_no_extras(repo_root: Path) -> None:
    """每日仅一个 schedule；不许 workflow_dispatch / retry / 多次自动触发。"""
    data = _load(repo_root, "daily-refresh.yml")
    trigger = data.get("on", data.get(True))
    assert set(trigger) == {"schedule"}, f"daily-refresh 触发器必须只有 schedule，实际: {set(trigger)}"
    schedules = trigger["schedule"]
    assert len(schedules) == 1, "只允许一个 cron"
    assert schedules[0]["cron"] == "17 2 * * *"


def test_daily_refresh_never_retries(repo_root: Path) -> None:
    """禁止 retry workflow / backoff / 失败后自动重试。"""
    text = (repo_root / ".github" / "workflows" / "daily-refresh.yml").read_text(encoding="utf-8")
    lowered = text.lower()
    for banned in ("retry:", "workflow_dispatch", "backoff", "max-attempt"):
        assert banned not in lowered, f"daily-refresh 不允许出现: {banned}"


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
