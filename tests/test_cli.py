"""CLI smoke tests — the CLI was previously 0% covered.

Uses Typer's in-process runner.  (The `python -m` entrypoint is regression-
tested in test_regressions.py.)
"""
import json

from typer.testing import CliRunner

from gastronomyml_compiler.cli import app

runner = CliRunner()


def test_cli_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "gastronomyml" in result.stdout.lower()


def test_cli_compile_writes_ir(tmp_path):
    out = tmp_path / "dish.ir.json"
    result = runner.invoke(app, [
        "compile", "Garlic butter salmon with lemon.", "--out", str(out), "--quiet",
    ])
    assert result.exit_code == 0, result.stdout
    assert out.exists()
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"]
    assert data["projections"]


def test_cli_compile_rejects_removed_llm_tier():
    """`--extractor llm` must error now that the tier is gone (not silently fall back)."""
    result = runner.invoke(app, ["compile", "tomato basil", "--extractor", "llm"])
    assert result.exit_code != 0


def test_cli_validate_roundtrip(tmp_path):
    out = tmp_path / "dish.ir.json"
    runner.invoke(app, ["compile", "Miso pork ramen with nori.", "--out", str(out), "--quiet"])
    result = runner.invoke(app, ["validate", str(out)])
    assert result.exit_code == 0
