"""USD/CNY conversion and the daily rate refresh.

config/exchange_rate.yaml is the ONLY source of truth for the USD -> CNY
factor used by every calculation (CNY = USD * usd_cny). It is updated once
per day by CI as a D-7 ~ D-1 average (Asia/Shanghai, complete calendar days)
of the observations the data source actually provides:

- no weekend filling, no interpolation
- never uses the current day
- no fallback, no retry — any failure fails the run
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from planscope.config import EXCHANGE_RATE_RELATIVE, find_repo_root

TIMEZONE = ZoneInfo("Asia/Shanghai")
WINDOW_DAYS = 7  # D-7 ~ D-1, both inclusive
RATE_DECIMALS = 6
FRANKFURTER_URL = "https://api.frankfurter.dev/v1/{start}..{end}?base=USD&symbols=CNY"


class RateFetchError(Exception):
    """Raised when the rate cannot be fetched or computed. No fallback."""


def today_shanghai() -> date:
    return datetime.now(TIMEZONE).date()


def observation_window(today: date | None = None) -> tuple[date, date]:
    """Return (D-7, D-1) — the 7 complete calendar days, never the current day."""
    current = today or today_shanghai()
    return current - timedelta(days=WINDOW_DAYS), current - timedelta(days=1)


def default_fetch(start: date, end: date) -> dict[date, float]:
    """Fetch raw daily USD/CNY values for the window. Single attempt, no retry."""
    url = FRANKFURTER_URL.format(start=start.isoformat(), end=end.isoformat())
    request = urllib.request.Request(url, headers={"User-Agent": "PlanScope/0.1"})
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as exc:
        raise RateFetchError(f"USD/CNY 数据源请求失败（不重试、不回退）: {url}: {exc}") from exc

    rates = payload.get("rates") if isinstance(payload, dict) else None
    if not isinstance(rates, dict):
        raise RateFetchError(f"USD/CNY 数据源返回格式异常: {url}")

    observations: dict[date, float] = {}
    for day_text, value in rates.items():
        try:
            day = date.fromisoformat(str(day_text))
        except ValueError:
            continue
        if not (start <= day <= end):
            continue  # outside D-7 ~ D-1
        if isinstance(value, dict):
            value = value.get("CNY")  # multi-symbol response: {"2026-09-16": {"CNY": 6.7}}
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
            continue  # invalid observation — never invent a replacement
        observations[day] = float(value)
    return observations


def weekly_average(observations: dict[date, float]) -> float:
    """sum(valid observations) / number of valid observations."""
    valid = [
        value
        for value in observations.values()
        if not isinstance(value, bool) and isinstance(value, (int, float)) and value > 0
    ]
    if not valid:
        raise RateFetchError("窗口内没有有效的 USD/CNY 日值（不补周末、不插值、不回退）")
    return sum(valid) / len(valid)


def format_rate(value: float) -> str:
    text = f"{value:.{RATE_DECIMALS}f}".rstrip("0")
    return text + "0" if text.endswith(".") else text


def write_exchange_rate(root: Path | str | None, value: float) -> Path:
    """Write config/exchange_rate.yaml containing exactly one key: usd_cny."""
    base = find_repo_root(root)
    path = base / EXCHANGE_RATE_RELATIVE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"usd_cny: {format_rate(value)}\n", encoding="utf-8")
    return path


def refresh_exchange_rate(
    root: Path | str | None = None,
    *,
    fetch=default_fetch,
    today: date | None = None,
) -> float:
    """Full D-7 ~ D-1 refresh. Errors propagate: CI must fail, never degrade."""
    base = find_repo_root(root)
    start, end = observation_window(today)
    observations = fetch(start, end)  # exactly one attempt
    average = weekly_average(observations)
    write_exchange_rate(base, average)
    return average


def to_cny(amount: object, currency: object, rate: float) -> float | None:
    """Derived CNY figure. Only currencies with a known rule are converted;
    anything else is not directly convertible — never guess a rate."""
    if isinstance(amount, bool) or not isinstance(amount, (int, float)):
        return None
    if not isinstance(currency, str):
        return None
    code = currency.upper()
    if code == "USD":
        return float(amount) * rate
    if code in {"CNY", "RMB", "CNH"}:
        return float(amount)
    return None
