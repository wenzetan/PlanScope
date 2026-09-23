"""Exchange-rate config loading (config/exchange_rate.yaml is the single source)."""

from pathlib import Path

import pytest

from planscope.config import ConfigError, find_repo_root, load_exchange_rate


def test_repo_rate_has_only_usd_cny(repo_root: Path) -> None:
    import yaml

    data = yaml.safe_load((repo_root / "config" / "exchange_rate.yaml").read_text(encoding="utf-8"))
    assert set(data) == {"usd_cny"}
    assert not isinstance(data["usd_cny"], bool)
    assert isinstance(data["usd_cny"], (int, float))
    assert data["usd_cny"] > 0


def test_missing_file_rejected(tmp_path: Path) -> None:
    # Explicit root must NOT fall back to another checkout.
    with pytest.raises(ConfigError):
        load_exchange_rate(tmp_path)


def test_find_repo_root_walks_up(tmp_path: Path) -> None:
    config = tmp_path / "config"
    config.mkdir(parents=True)
    (config / "exchange_rate.yaml").write_text("usd_cny: 7.0\n", encoding="utf-8")
    nested = tmp_path / "a" / "b"
    nested.mkdir(parents=True)
    assert find_repo_root(nested) == tmp_path
