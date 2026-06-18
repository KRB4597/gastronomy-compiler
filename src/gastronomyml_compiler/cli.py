"""GastronomyML compiler CLI.

Analogous to ErisML cli.py.  Entry point: ``gastronomy-compile``.

Subcommands
-----------
compile     Compile a natural-language dish description to GastronomyIR JSON
validate    Validate an existing IR JSON file
report      Print a human-readable summary of an IR file
export-schema-org  Re-export an IR as Schema.org/Recipe JSON-LD
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from . import SCHEMA_VERSION, __version__
from .export import export_json, export_schema_org
from .ir.schemas import GastronomyIR
from .pipeline.orchestrator import compile_document
from .tiers import ALL_PROJECTIONS, CompilerTier

app = typer.Typer(
    name="gastronomy-compile",
    help="GastronomyML compiler — natural-language culinary modeling language",
    add_completion=False,
)
console = Console()


# ---------------------------------------------------------------------------
# compile
# ---------------------------------------------------------------------------

@app.command()
def compile(
    input: Annotated[str, typer.Argument(help="Input file path or inline text")],
    out: Annotated[Optional[str], typer.Option("--out", "-o", help="Output IR JSON path")] = None,
    extractor: Annotated[CompilerTier, typer.Option("--extractor", help="Extraction tier")] = CompilerTier.RULE,
    projection: Annotated[
        Optional[str],
        typer.Option(
            "--projection",
            help=(
                "Comma-separated projections to run at compile time. "
                "Available: flavor_similarity, flavor_contrast, cultural_harmony, nutritional_balance. "
                "Default: all four."
            ),
        ),
    ] = None,
    title: Annotated[Optional[str], typer.Option("--title", help="Document title override")] = None,
    quiet: Annotated[bool, typer.Option("--quiet", "-q", help="Suppress progress output")] = False,
) -> None:
    """Compile a natural-language dish description to GastronomyIR JSON."""

    proj_list: list[str] | None = None
    if projection:
        proj_list = [p.strip() for p in projection.split(",")]
        unknown = set(proj_list) - set(ALL_PROJECTIONS)
        if unknown:
            console.print(f"[red]Unknown projection(s): {unknown}[/red]")
            console.print(f"Available: {', '.join(ALL_PROJECTIONS)}")
            raise typer.Exit(1)

    if not quiet:
        console.print(f"[bold cyan]GastronomyML Compiler[/bold cyan] v{__version__}")
        console.print(f"  extractor : {extractor.value}")
        console.print(f"  projections: {', '.join(proj_list or ALL_PROJECTIONS)}")
        console.print()

    try:
        ir = compile_document(
            input,
            extractor=extractor,
            projections=proj_list,
            title=title,
        )
    except Exception as exc:
        console.print(f"[red]Compilation failed: {exc}[/red]")
        raise typer.Exit(1)

    # Output
    json_out = export_json(ir, path=out)
    if out:
        if not quiet:
            console.print(f"[green]IR written to {out}[/green]")
    else:
        print(json_out)

    # Print summary
    if not quiet:
        _print_summary(ir)


# ---------------------------------------------------------------------------
# validate
# ---------------------------------------------------------------------------

@app.command()
def validate(
    ir_file: Annotated[str, typer.Argument(help="Path to GastronomyIR JSON")],
) -> None:
    """Validate an existing IR JSON file against the GastronomyIR schema."""
    path = Path(ir_file)
    if not path.exists():
        console.print(f"[red]File not found: {ir_file}[/red]")
        raise typer.Exit(1)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        GastronomyIR.model_validate(data)
        console.print(f"[green]✓ Valid GastronomyIR ({SCHEMA_VERSION})[/green]")
    except Exception as exc:
        console.print(f"[red]Validation failed: {exc}[/red]")
        raise typer.Exit(1)


# ---------------------------------------------------------------------------
# report
# ---------------------------------------------------------------------------

@app.command()
def report(
    ir_file: Annotated[str, typer.Argument(help="Path to GastronomyIR JSON")],
) -> None:
    """Print a human-readable summary of an IR file."""
    path = Path(ir_file)
    if not path.exists():
        console.print(f"[red]File not found: {ir_file}[/red]")
        raise typer.Exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    ir = GastronomyIR.model_validate(data)
    _print_summary(ir)


# ---------------------------------------------------------------------------
# export-schema-org
# ---------------------------------------------------------------------------

@app.command(name="export-schema-org")
def export_schema_org_cmd(
    ir_file: Annotated[str, typer.Argument(help="Path to GastronomyIR JSON")],
    out: Annotated[str, typer.Option("--out", "-o", help="Output path")] = "recipe.jsonld",
) -> None:
    """Export an IR as Schema.org/Recipe JSON-LD."""
    path = Path(ir_file)
    if not path.exists():
        console.print(f"[red]File not found: {ir_file}[/red]")
        raise typer.Exit(1)

    data = json.loads(path.read_text(encoding="utf-8"))
    ir = GastronomyIR.model_validate(data)
    export_schema_org(ir, path=out)
    console.print(f"[green]Schema.org/Recipe written to {out}[/green]")


# ---------------------------------------------------------------------------
# version
# ---------------------------------------------------------------------------

@app.command()
def version() -> None:
    """Print compiler version."""
    console.print(f"gastronomyml-compiler {__version__} ({SCHEMA_VERSION})")


# ---------------------------------------------------------------------------
# Shared summary renderer
# ---------------------------------------------------------------------------

def _print_summary(ir: GastronomyIR) -> None:
    console.print()
    console.print(Panel(
        f"[bold]{ir.document.title}[/bold]\n"
        f"Cuisine: {ir.document.cuisine or 'unknown'}  |  "
        f"Ingredients: {len(ir.ingredients)}  |  "
        f"Techniques: {len(ir.techniques)}",
        title="[cyan]GastronomyIR Summary[/cyan]",
    ))

    # Flavor vector table
    fv = ir.aggregate_flavor_vector
    table = Table(title="Aggregate Flavor Vector", show_header=True, header_style="bold magenta")
    table.add_column("Dimension", style="cyan")
    table.add_column("Value", justify="right")
    table.add_column("Direction")
    table.add_column("Explanation")

    for dim in ["sweet", "salty", "sour", "bitter", "umami", "fat", "heat", "aromatic", "texture"]:
        ds = getattr(fv, dim)
        bar = "█" * int(abs(ds.value) * 10)
        table.add_row(
            dim,
            f"{ds.value:+.2f} {bar}",
            ds.direction,
            ds.explanation or "",
        )
    console.print(table)

    # Projections table
    if ir.projections:
        pt = Table(title="Projection Results", show_header=True, header_style="bold magenta")
        pt.add_column("Projection", style="cyan")
        pt.add_column("Verdict")
        pt.add_column("Polarity")
        pt.add_column("Score", justify="right")
        for pid, pr in ir.projections.items():
            color = {"harmonious": "green", "discordant": "red"}.get(pr.polarity, "yellow")
            pt.add_row(pid, pr.verdict, f"[{color}]{pr.polarity}[/{color}]", f"{pr.score:+.3f}")
        console.print(pt)

    # Harmony verdict
    if ir.harmony_verdict:
        hv = ir.harmony_verdict
        color = {"harmonious": "green", "complementary": "green",
                 "discordant": "red", "clashing": "red"}.get(hv.verdict.value, "yellow")
        console.print(Panel(
            f"[bold {color}]{hv.verdict.value.upper()}[/bold {color}]  "
            f"(confidence={hv.confidence:.2f})\n\n{hv.explanation}",
            title="[cyan]Harmony Verdict[/cyan]",
        ))

    if ir.cross_projection_disagreement:
        console.print("[yellow]⚠ Projections disagree on polarity — see cross_projection_disagreement in IR.[/yellow]")
