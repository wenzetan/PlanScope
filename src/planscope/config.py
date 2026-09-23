"""Configuration loading.

``config/exchange_rate.yaml`` is the ONLY source of truth for the fixed
USD -> CNY conversion factor. Never hardcode 7.0 anywhere else.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml

ENV_ROOT = "PLANSCOPE_ROOT"
EXCHANGE_RATE_RELATIVE = Path("config") / "exchange_rate.yaml"


class ConfigError(Exception):
    """Raised when a configuration file is missing or malformed."""


def find_repo_root(start: Path | str | None = None) -> Path:
    """Locate the repository root (the directory containing config/).

    Precedence: explicit ``start`` > ``PLANSCOPE_ROOT`` env > cwd > package location.
    An explicit ``start`` never falls back to other candidates, so a broken
    tree is reported instead of silently resolving to another checkout.
    """
    if start is not None:
        candidates: list[Path] = [Path(start)]
    else:
        env = os.environ.get(ENV_ROOT)
        candidates = [Path(env)] if env else [Path.cwd(), Path(__file__).resolve()]

    for candidate in candidates:
        directory = candidate if candidate.is_dir() else candidate.parent
        for parent in (directory, *directory.parents):
            if (parent / EXCHANGE_RATE_RELATIVE).is_file():
                return parent
    raise ConfigError(
        "无法定位仓库根目录：未找到 config/exchange_rate.yaml。"
        f" 可通过 {ENV_ROOT} 环境变量或 --root 参数显式指定。"
    )


def load_exchange_rate(root: Path | str | None = None) -> float:
    """Load and validate config/exchange_rate.yaml.

    The file must contain exactly one key: ``usd_cny`` (a positive number).
    """
    base = find_repo_root(root)
    path = base / EXCHANGE_RATE_RELATIVE
    if not path.is_file():
        raise ConfigError(f"缺少汇率配置文件: {path}")

    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        raise ConfigError(f"汇率配置文件无法解析: {path}: {exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"汇率配置文件必须是映射: {path}")

    extra = sorted(set(data) - {"usd_cny"})
    if extra:
        raise ConfigError(
            f"汇率配置文件包含多余字段: {path}: {', '.join(extra)}（只允许 usd_cny）"
        )
    if "usd_cny" not in data:
        raise ConfigError(f"汇率配置文件缺少字段: {path}: usd_cny")

    value = data["usd_cny"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"汇率配置字段类型错误: {path}: usd_cny 必须是数字，实际为 {value!r}")
    if value <= 0:
        raise ConfigError(f"汇率配置字段取值错误: {path}: usd_cny 必须为正数，实际为 {value!r}")
    return float(value)


def usd_to_cny(amount: float, rate: float | None = None, root: Path | str | None = None) -> float:
    """Convert USD to CNY using config/exchange_rate.yaml (single source).

    The result is a fixed, approximate comparison figure — not a real-time
    payment or settlement rate.
    """
    factor = load_exchange_rate(root) if rate is None else float(rate)
    return float(amount) * factor
