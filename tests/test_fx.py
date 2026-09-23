"""USD/CNY fetcher: D-7 ~ D-1 window, 7-day average, single source of truth."""

from datetime import date
from pathlib import Path

import pytest

from planscope.config import ConfigError, load_exchange_rate, usd_to_cny
from planscope.fx import (
    RateFetchError,
    format_rate,
    observation_window,
    refresh_exchange_rate,
    weekly_average,
    write_exchange_rate,
)


def _write_rate(tmp_path: Path, content: str) -> None:
    config = tmp_path / "config"
    config.mkdir(parents=True, exist_ok=True)
    (config / "exchange_rate.yaml").write_text(content, encoding="utf-8")


def test_observation_window_is_d7_to_d1() -> None:
    start, end = observation_window(date(2026, 9, 23))
    assert start == date(2026, 9, 16)
    assert end == date(2026, 9, 22)
    assert (end - start).days == 6  # exactly 7 complete days, never today


def test_weekend_days_are_not_filled() -> None:
    """Only observations the source actually returned are averaged."""
    observations = {
        date(2026, 9, 16): 6.70,
        date(2026, 9, 17): 6.72,
        date(2026, 9, 18): 6.68,
        # 19/20 = weekend: absent, never invented
        date(2026, 9, 21): 6.71,
        date(2026, 9, 22): 6.69,
    }
    average = weekly_average(observations)
    assert average == pytest.approx(sum(observations.values()) / 5)


def test_empty_window_fails_loudly() -> None:
    with pytest.raises(RateFetchError):
        weekly_average({})


def test_invalid_values_are_excluded_not_repaired() -> None:
    with pytest.raises(RateFetchError):
        weekly_average({date(2026, 9, 16): 0, date(2026, 9, 17): -1})


def test_format_rate_keeps_yaml_number_shape() -> None:
    assert format_rate(6.70154) == "6.70154"
    assert format_rate(7.0) == "7.0"
    assert format_rate(6.842137) == "6.842137"


def test_write_exchange_rate_single_key(tmp_path: Path) -> None:
    _write_rate(tmp_path, "usd_cny: 7.0\n")
    import yaml

    path = write_exchange_rate(tmp_path, 6.842137)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert set(data) == {"usd_cny"}
    assert data["usd_cny"] == pytest.approx(6.842137)
    assert path.read_text(encoding="utf-8").strip() == "usd_cny: 6.842137"


def test_refresh_uses_fetcher_and_writes_config(tmp_path: Path) -> None:
    _write_rate(tmp_path, "usd_cny: 7.0\n")
    calls: list[tuple[date, date]] = []

    def fake_fetch(start: date, end: date) -> dict[date, float]:
        calls.append((start, end))
        return {start: 6.5, end: 6.7}

    average = refresh_exchange_rate(tmp_path, fetch=fake_fetch, today=date(2026, 9, 23))
    assert average == pytest.approx(6.6)
    assert len(calls) == 1  # exactly one attempt
    assert calls[0] == (date(2026, 9, 16), date(2026, 9, 22))
    assert load_exchange_rate(tmp_path) == pytest.approx(6.6)


def test_refresh_does_not_retry_on_failure(tmp_path: Path) -> None:
    _write_rate(tmp_path, "usd_cny: 7.0\n")
    calls = {"count": 0}

    def failing_fetch(start: date, end: date) -> dict[date, float]:
        calls["count"] += 1
        raise RateFetchError("source down")

    with pytest.raises(RateFetchError):
        refresh_exchange_rate(tmp_path, fetch=failing_fetch, today=date(2026, 9, 23))
    assert calls["count"] == 1  # no retry, no fallback
    assert load_exchange_rate(tmp_path) == pytest.approx(7.0)  # config untouched


def test_usd_to_cny_reads_config_only(tmp_path: Path) -> None:
    _write_rate(tmp_path, "usd_cny: 7.0\n")
    assert usd_to_cny(20, root=tmp_path) == pytest.approx(140.0)
    assert usd_to_cny(50, root=tmp_path) == pytest.approx(350.0)
    assert usd_to_cny(100, root=tmp_path) == pytest.approx(700.0)

    _write_rate(tmp_path, "usd_cny: 6.5\n")
    assert usd_to_cny(10, root=tmp_path) == pytest.approx(65.0)  # follows config, not a hardcode


def test_repo_rate_config_is_valid() -> None:
    rate = load_exchange_rate(Path(__file__).resolve().parents[1])
    assert rate > 0
    assert isinstance(rate, float)


@pytest.mark.parametrize(
    "content",
    [
        "usd_cny: 7.0\nsource: https://example.com\n",  # extra field
        "usd_cny: -1\n",
        "usd_cny: 0\n",
        "usd_cny: abc\n",
        "rate: 7.0\n",
        "",
    ],
)
def test_invalid_rate_config_rejected(tmp_path: Path, content: str) -> None:
    _write_rate(tmp_path, content)
    with pytest.raises(ConfigError):
        load_exchange_rate(tmp_path)
