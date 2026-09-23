import json
import os
import subprocess
import sys
from pathlib import Path

from planscope.cli import main


def test_cli_validate_passes(repo_root: Path, capsys) -> None:
    code = main(["--root", str(repo_root), "validate"])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert "OK" in captured.out


def test_cli_list_providers(repo_root: Path, capsys) -> None:
    code = main(["--root", str(repo_root), "list", "providers"])
    captured = capsys.readouterr()
    assert code == 0
    assert "openai" in captured.out
    assert "provider_id" in captured.out or "id" in captured.out


def test_cli_list_plans(repo_root: Path, capsys) -> None:
    code = main(["--root", str(repo_root), "list", "plans"])
    captured = capsys.readouterr()
    assert code == 0
    assert "openai/example-coding-plan" in captured.out


def test_cli_requires_command(repo_root: Path) -> None:
    assert main(["--root", str(repo_root)]) == 2


def test_cli_fetch_rate_dry_run(repo_root: Path, capsys) -> None:
    """--dry-run prints the D-7 ~ D-1 window without touching the network."""
    code = main(["--root", str(repo_root), "fetch-rate", "--dry-run"])
    captured = capsys.readouterr()
    assert code == 0
    assert "观察窗口" in captured.out
    # config must be untouched by a dry run
    assert (repo_root / "config" / "exchange_rate.yaml").is_file()


def test_cli_export_site_data(tmp_path: Path, repo_root: Path, capsys) -> None:
    out = tmp_path / "site_data.json"
    code = main(["--root", str(repo_root), "export-site-data", "--out", str(out)])
    captured = capsys.readouterr()
    assert code == 0, captured.err
    assert out.is_file()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["stats"]["providers"] >= 8
    assert data["stats"]["plans"] >= 1
    assert data["exchange_rate"]["usd_cny"] > 0


def test_cli_export_refuses_invalid_tree(tmp_path: Path, repo_root: Path, capsys) -> None:
    import shutil

    root = tmp_path / "broken"
    shutil.copytree(repo_root / "schemas", root / "schemas")
    shutil.copytree(repo_root / "data", root / "data")
    (root / "config").mkdir()
    (root / "config" / "exchange_rate.yaml").write_text("usd_cny: 7.0\nsource: x\n", encoding="utf-8")

    out = tmp_path / "site_data.json"
    code = main(["--root", str(root), "export-site-data", "--out", str(out)])
    captured = capsys.readouterr()
    assert code == 1
    assert not out.exists(), "校验失败时不得导出"


def test_module_entrypoint(repo_root: Path) -> None:
    env = {**os.environ, "PYTHONPATH": str(repo_root / "src")}
    result = subprocess.run(
        [sys.executable, "-m", "planscope", "validate"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "OK" in result.stdout
