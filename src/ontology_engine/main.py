"""
Ontology Engine CLI — generates OWL ontologies from Markdown documents using Claude Agent SDK.

Usage:
    # Generate ontology from a single Markdown file
    uv run ontology-engine generate data/run_dir/document.md

    # Generate ontologies for all .md files in a run directory
    uv run ontology-engine generate-all data/run_dir/

    # With options
    uv run ontology-engine generate data/run_dir/document.md --output-dir output/
"""

import asyncio
import sys
from pathlib import Path

import click
from dotenv import load_dotenv

from ontology_engine.config import DEFAULT_MODEL, DEFAULT_MAX_TURNS

load_dotenv()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Ontology Engine — agentic Markdown-to-OWL pipeline."""
    pass


@cli.command()
@click.argument("md_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory. Defaults to the parent directory of the input file.",
)
@click.option(
    "--model", "-m",
    default=DEFAULT_MODEL,
    show_default=True,
    help="Claude model to use for generation.",
)
@click.option(
    "--max-turns", "-t",
    type=int,
    default=DEFAULT_MAX_TURNS,
    show_default=True,
    help="Max agent turns per phase.",
)
def generate(md_file: Path, output_dir: Path | None, model: str, max_turns: int):
    """Generate an OWL ontology from a single Markdown file."""
    from ontology_engine.agent import generate_ontology
    from ontology_engine.utils import console

    md_file = md_file.resolve()
    if output_dir is None:
        output_dir = md_file.parent
    else:
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

    result = asyncio.run(
        generate_ontology(
            md_path=md_file,
            output_dir=output_dir,
            model=model,
            max_turns=max_turns,
        )
    )

    if result.success:
        console.print(f"\n[bold green]Success![/bold green]")
        console.print(f"  JSON-LD: {result.json_path}")
        console.print(f"  OWL:     {result.owl_path}")
        console.print(f"  Stats:   {result.stats}")
        sys.exit(0)
    else:
        console.print(f"\n[bold red]Failed:[/bold red] {result.error}")
        sys.exit(1)


@cli.command("generate-all")
@click.argument("run_dir", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output-dir", "-o",
    type=click.Path(path_type=Path),
    default=None,
    help="Output directory. Defaults to the run directory itself.",
)
@click.option(
    "--model", "-m",
    default=DEFAULT_MODEL,
    show_default=True,
    help="Claude model to use for generation.",
)
@click.option(
    "--max-turns", "-t",
    type=int,
    default=DEFAULT_MAX_TURNS,
    show_default=True,
    help="Max agent turns per phase.",
)
def generate_all(run_dir: Path, output_dir: Path | None, model: str, max_turns: int):
    """Generate ontologies for all Markdown files in a run directory."""
    from ontology_engine.agent import generate_all_ontologies
    from ontology_engine.utils import console

    run_dir = run_dir.resolve()
    if output_dir is not None:
        output_dir = output_dir.resolve()
        output_dir.mkdir(parents=True, exist_ok=True)

    results = asyncio.run(
        generate_all_ontologies(
            run_dir=run_dir,
            output_dir=output_dir,
            model=model,
            max_turns=max_turns,
        )
    )

    total = len(results["success"]) + len(results["failed"]) + len(results["skipped"])
    if results["failed"]:
        console.print(f"\n[bold red]{len(results['failed'])}/{total} failed.[/bold red]")
        sys.exit(1)
    else:
        console.print(f"\n[bold green]All {len(results['success'])}/{total} succeeded![/bold green]")
        sys.exit(0)


if __name__ == "__main__":
    cli()
