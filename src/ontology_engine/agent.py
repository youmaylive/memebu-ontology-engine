"""
Agent runner with externally enforced validation loop.

The agent generates JSON-LD ontologies. Validation is run by Python code
via rdflib — the agent cannot skip or circumvent it.

Flow:
  1. Agent reads the Markdown file and generates a JSON-LD ontology (generation phase)
  2. Python validates with rdflib + structural checks
  3. If errors: Python feeds them back to the agent as a fix prompt
  4. Repeat 2-3 until validation passes or max attempts exhausted
  5. Convert validated JSON-LD to OWL/RDF-XML
"""

import asyncio
from pathlib import Path

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
)

from ontology_engine.config import (
    PROJECT_ROOT,
    DEFAULT_MODEL,
    DEFAULT_MAX_TURNS,
    MAX_VALIDATION_ATTEMPTS,
    MAX_CONTINUATION_ATTEMPTS,
    MAX_ENRICHMENT_ATTEMPTS,
)
from ontology_engine.converter import convert_to_owl
from ontology_engine.models import OntologyResult
from ontology_engine.prompts.fix import (
    build_continuation_prompt,
    build_enrichment_prompt,
    build_fix_prompt,
)
from ontology_engine.prompts.generation import build_generation_prompt
from ontology_engine.prompts.system import build_system_prompt
from ontology_engine.utils import compute_minimums, console, count_lines, derive_namespace
from ontology_engine.validator import validate_ontology


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agent_options(
    model: str,
    max_turns: int,
    session_id: str | None = None,
) -> ClaudeAgentOptions:
    """Build common agent options, optionally resuming a session."""
    opts = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        permission_mode="acceptEdits",
        model=model,
        system_prompt=build_system_prompt(),
        max_turns=max_turns,
        cwd=str(PROJECT_ROOT),
    )
    if session_id:
        opts.resume = session_id
    return opts


async def _run_agent(prompt: str, options: ClaudeAgentOptions) -> tuple[bool, str | None]:
    """Run a single agent invocation.

    Returns
    -------
    (success, session_id)
        success: whether the agent reported success
        session_id: captured session id for resumption
    """
    success = False
    session_id = None

    try:
        async for message in query(prompt=prompt, options=options):
            # Capture session ID from the init message
            if hasattr(message, "subtype") and message.subtype == "init":
                if hasattr(message, "session_id"):
                    session_id = message.session_id

            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        console.print(block.text)
                    elif hasattr(block, "name"):
                        console.print(f"\n  [dim]Tool: {block.name}[/dim]")

            elif isinstance(message, ResultMessage):
                if message.subtype == "success":
                    success = True
                else:
                    console.print(
                        f"\n  [yellow]Agent finished with status: {message.subtype}[/yellow]"
                    )
                if hasattr(message, "total_cost_usd") and message.total_cost_usd:
                    console.print(f"  [dim]Cost: ${message.total_cost_usd:.4f}[/dim]")

    except Exception as exc:
        console.print(f"\n  [red]Agent SDK error: {exc}[/red]")

    return success, session_id


# ---------------------------------------------------------------------------
# Single ontology generation
# ---------------------------------------------------------------------------


async def generate_ontology(
    md_path: Path,
    output_dir: Path,
    model: str = DEFAULT_MODEL,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> OntologyResult:
    """Generate an ontology from a single Markdown file with externally enforced validation.

    Steps:
      1. Agent reads Markdown + generates JSON-LD, writes file
      2. Python validates via rdflib (agent cannot skip this)
      3. On failure: Python feeds errors to agent, agent fixes, repeat
      4. On success: Convert JSON-LD to OWL/RDF-XML
    """
    # Derive paths and metadata
    stem = md_path.stem
    namespace = derive_namespace(md_path.name)
    line_count = count_lines(md_path)
    minimums = compute_minimums(line_count)

    json_dir = output_dir / "ontology_json"
    json_dir.mkdir(parents=True, exist_ok=True)
    json_path = json_dir / f"{stem}.json"
    owl_path = output_dir / f"{stem}.owl"

    console.rule(f"[bold]Generating ontology: {md_path.name}[/bold]")
    console.print(f"  Source:     {md_path}")
    console.print(f"  Output:     {json_path}")
    console.print(f"  Namespace:  {namespace}")
    console.print(f"  Lines:      {line_count:,}")
    console.print(f"  Minimums:   {minimums}")
    console.print(f"  Model:      {model}")
    console.print()

    # ------------------------------------------------------------------
    # Phase 1: Generation
    # ------------------------------------------------------------------
    console.print("[bold]Phase 1:[/bold] Generating JSON-LD ontology...\n")

    gen_prompt = build_generation_prompt(
        md_path=md_path,
        output_path=json_path,
        namespace=namespace,
        minimums=minimums,
        line_count=line_count,
    )

    agent_ok, session_id = await _run_agent(
        prompt=gen_prompt,
        options=_agent_options(model=model, max_turns=max_turns),
    )

    # Handle non-success (token overflow / max turns) with continuation
    if not agent_ok:
        for cont_attempt in range(1, MAX_CONTINUATION_ATTEMPTS + 1):
            console.print(
                f"\n  [yellow]Continuation attempt {cont_attempt}/{MAX_CONTINUATION_ATTEMPTS}...[/yellow]\n"
            )
            cont_prompt = build_continuation_prompt(output_path=json_path)
            agent_ok, session_id = await _run_agent(
                prompt=cont_prompt,
                options=_agent_options(
                    model=model,
                    max_turns=max_turns,
                    session_id=session_id,
                ),
            )
            if agent_ok:
                break

        if not agent_ok:
            console.print("\n  [red]Agent failed during generation phase.[/red]")
            # Still attempt validation — the file may exist on disk
            if not json_path.exists():
                return OntologyResult(
                    success=False,
                    namespace=namespace,
                    error="Agent failed to generate ontology file.",
                )

    # ------------------------------------------------------------------
    # Phase 2 & 3: External validation loop
    # ------------------------------------------------------------------
    for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
        console.print(f"\n{'─' * 50}")
        console.print(
            f"[bold]Validation attempt {attempt}/{MAX_VALIDATION_ATTEMPTS}[/bold]"
        )
        console.print(f"{'─' * 50}")

        result = validate_ontology(
            json_path=json_path,
            min_classes=minimums["min_classes"],
            min_properties=minimums["min_properties"],
            min_individuals=minimums["min_individuals"],
        )

        if result.success:
            console.print(f"\n  [green]Validation passed![/green]")
            console.print(f"  {result.raw_output}")

            # ----------------------------------------------------------
            # Phase 2b: Connectivity check & enrichment
            # ----------------------------------------------------------
            if result.connectivity.get("is_sparse"):
                console.print(f"\n  [yellow]Graph is sparse — triggering enrichment.[/yellow]")
                console.print(f"\n{result.connectivity_report}\n")

                for enrich_attempt in range(1, MAX_ENRICHMENT_ATTEMPTS + 1):
                    console.print(
                        f"\n[bold]Phase 2b:[/bold] Enrichment attempt "
                        f"{enrich_attempt}/{MAX_ENRICHMENT_ATTEMPTS}...\n"
                    )

                    enrich_prompt = build_enrichment_prompt(
                        output_path=json_path,
                        connectivity_report=result.connectivity_report,
                    )

                    enrich_ok, session_id = await _run_agent(
                        prompt=enrich_prompt,
                        options=_agent_options(
                            model=model,
                            max_turns=max_turns,
                            session_id=session_id,
                        ),
                    )

                    # Re-validate after enrichment
                    result = validate_ontology(
                        json_path=json_path,
                        min_classes=minimums["min_classes"],
                        min_properties=minimums["min_properties"],
                        min_individuals=minimums["min_individuals"],
                    )

                    if not result.success:
                        console.print(
                            f"  [red]Enrichment broke validation — "
                            f"will continue to fix loop.[/red]"
                        )
                        break

                    if not result.connectivity.get("is_sparse"):
                        console.print(
                            f"  [green]Enrichment improved connectivity![/green]"
                        )
                        console.print(f"\n{result.connectivity_report}\n")
                        break

                    console.print(
                        f"  [yellow]Still sparse after enrichment attempt "
                        f"{enrich_attempt}.[/yellow]"
                    )
                    console.print(f"\n{result.connectivity_report}\n")

                # If enrichment broke validation, fall through to the fix loop
                if not result.success:
                    continue
            else:
                console.print(f"\n{result.connectivity_report}\n")

            # Convert to OWL/RDF-XML
            try:
                convert_to_owl(json_path=json_path, owl_path=owl_path)
            except Exception as exc:
                return OntologyResult(
                    success=False,
                    json_path=json_path,
                    namespace=namespace,
                    stats=result.stats,
                    error=f"OWL conversion failed: {exc}",
                )

            return OntologyResult(
                success=True,
                json_path=json_path,
                owl_path=owl_path,
                namespace=namespace,
                stats=result.stats,
            )

        console.print(f"\n  [red]Validation failed ({result.error_count} error(s)):[/red]")
        for line in result.raw_output.splitlines()[:25]:
            console.print(f"    {line}")
        if len(result.raw_output.splitlines()) > 25:
            console.print(
                f"    ... ({len(result.raw_output.splitlines()) - 25} more lines)"
            )

        if attempt == MAX_VALIDATION_ATTEMPTS:
            console.print(
                f"\n  [red]Exhausted {MAX_VALIDATION_ATTEMPTS} validation attempts.[/red]"
            )
            return OntologyResult(
                success=False,
                json_path=json_path,
                namespace=namespace,
                stats=result.stats,
                error=f"Validation failed after {MAX_VALIDATION_ATTEMPTS} attempts.",
            )

        # Phase 3: Feed errors back to agent for fixing
        console.print(
            f"\n[bold]Phase 3:[/bold] Sending errors to agent for fixing (attempt {attempt})...\n"
        )

        fix_prompt = build_fix_prompt(
            output_path=json_path,
            validation_errors=result.raw_output,
            attempt=attempt,
        )

        # Resume the same session so the agent has full context
        fix_ok, session_id = await _run_agent(
            prompt=fix_prompt,
            options=_agent_options(
                model=model,
                max_turns=max_turns,
                session_id=session_id,
            ),
        )

        if not fix_ok:
            console.print(
                f"  [yellow]Agent reported issues during fix attempt {attempt}, "
                f"re-validating anyway...[/yellow]"
            )

    # Should not reach here, but just in case
    return OntologyResult(
        success=False,
        json_path=json_path,
        namespace=namespace,
        error="Unexpected: exited validation loop without result.",
    )


# ---------------------------------------------------------------------------
# Batch generation
# ---------------------------------------------------------------------------


async def generate_all_ontologies(
    run_dir: Path,
    output_dir: Path | None = None,
    model: str = DEFAULT_MODEL,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> dict[str, list[str]]:
    """Generate ontologies for all Markdown files in a run directory.

    Parameters
    ----------
    run_dir:
        Directory containing .md files from Step 1 (PDF-to-Markdown).
    output_dir:
        Where to write outputs. Defaults to run_dir itself.
    model:
        Claude model to use.
    max_turns:
        Max agent turns per phase.

    Returns
    -------
    dict with keys: success, failed, skipped (lists of filenames).
    """
    if output_dir is None:
        output_dir = run_dir

    md_files = sorted(run_dir.glob("*.md"))

    if not md_files:
        console.print(f"[yellow]No .md files found in {run_dir}[/yellow]")
        return {"success": [], "failed": [], "skipped": []}

    console.rule("[bold]Batch Ontology Generation[/bold]")
    console.print(f"  Run directory: {run_dir}")
    console.print(f"  Output:        {output_dir}")
    console.print(f"  Files found:   {len(md_files)}")
    console.print()

    results: dict[str, list[str]] = {"success": [], "failed": [], "skipped": []}

    for md_path in md_files:
        result = await generate_ontology(
            md_path=md_path,
            output_dir=output_dir,
            model=model,
            max_turns=max_turns,
        )

        if result.success:
            results["success"].append(md_path.name)
        else:
            results["failed"].append(md_path.name)
            console.print(f"  [red]Error: {result.error}[/red]")

    # Summary
    console.rule("[bold]Batch Results[/bold]")
    console.print(f"  [green]Success:[/green] {len(results['success'])} files")
    console.print(f"  [red]Failed:[/red]  {len(results['failed'])} files")
    console.print(f"  [yellow]Skipped:[/yellow] {len(results['skipped'])} files")

    if results["failed"]:
        console.print(f"\n  Failed files: {', '.join(results['failed'])}")

    return results
