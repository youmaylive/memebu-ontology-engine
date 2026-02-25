"""
Agent runner with externally enforced validation loop and LLM-based review.

The agent generates JSON-LD ontologies. Structural validation is run by
Python code via rdflib. Qualitative review is handled by a separate LLM
reviewer agent with clean context.

Flow:
  1. Agent reads the Markdown file and generates a JSON-LD ontology
  2. Python validates structural correctness (rdflib, domain/range, labels)
  3. If structural errors: feed them back to the agent, repeat
  4. Connectivity/sparsity check: if sparse, enrichment loop
  5. LLM reviewer (fresh agent) assesses coverage & quality
  6. If reviewer says NEEDS_IMPROVEMENT: feed feedback to generator, repeat 2-5
  7. Convert validated + reviewed JSON-LD to OWL/RDF-XML
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
    MAX_REVIEW_ATTEMPTS,
)
from ontology_engine.converter import convert_to_owl
from ontology_engine.models import OntologyResult
from ontology_engine.prompts.fix import (
    build_continuation_prompt,
    build_enrichment_prompt,
    build_fix_prompt,
    build_review_feedback_prompt,
)
from ontology_engine.prompts.generation import build_generation_prompt
from ontology_engine.prompts.review import build_review_prompt
from ontology_engine.prompts.system import build_system_prompt
from ontology_engine.utils import console, count_lines, derive_namespace
from ontology_engine.validator import validate_ontology


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Rolling idle timeout: if no message arrives from Claude for this many seconds,
# the stream is considered dead and we raise asyncio.TimeoutError.
# This prevents the pipeline from hanging for hours/days on a stale connection.
IDLE_TIMEOUT_SECONDS = 10 * 60  # 10 minutes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class StreamIdleTimeout(Exception):
    """Raised when the Claude Agent SDK stream produces no messages for too long."""
    pass


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
        # Use rolling idle timeout: if no message for IDLE_TIMEOUT_SECONDS,
        # the stream is dead — raise StreamIdleTimeout so caller can retry.
        stream = query(prompt=prompt, options=options).__aiter__()
        while True:
            try:
                message = await asyncio.wait_for(
                    stream.__anext__(), timeout=IDLE_TIMEOUT_SECONDS
                )
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                console.print(
                    f"\n  [red]⏰ Stream idle for {IDLE_TIMEOUT_SECONDS // 60} min "
                    f"— connection appears dead.[/red]"
                )
                raise StreamIdleTimeout(
                    f"No response from Claude for {IDLE_TIMEOUT_SECONDS // 60} minutes"
                )

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

    except StreamIdleTimeout:
        raise  # Let caller handle retry
    except Exception as exc:
        console.print(f"\n  [red]Agent SDK error: {exc}[/red]")

    return success, session_id


async def _run_review(
    prompt: str,
    model: str,
) -> tuple[bool, str]:
    """Run the LLM reviewer agent with a fresh session (clean context).

    The reviewer is read-only — it can only Read, Grep, and Glob.

    Returns
    -------
    (approved, feedback)
        approved: True if the reviewer output contains "VERDICT: APPROVED"
        feedback: the full text output from the reviewer
    """
    opts = ClaudeAgentOptions(
        allowed_tools=["Read", "Grep", "Glob"],
        permission_mode="bypassPermissions",
        model=model,
        max_turns=DEFAULT_MAX_TURNS,
        cwd=str(PROJECT_ROOT),
    )

    feedback_parts: list[str] = []

    try:
        # Use rolling idle timeout for reviewer too
        stream = query(prompt=prompt, options=opts).__aiter__()
        while True:
            try:
                message = await asyncio.wait_for(
                    stream.__anext__(), timeout=IDLE_TIMEOUT_SECONDS
                )
            except StopAsyncIteration:
                break
            except asyncio.TimeoutError:
                console.print(
                    f"\n  [red]⏰ Review stream idle for {IDLE_TIMEOUT_SECONDS // 60} min "
                    f"— connection appears dead.[/red]"
                )
                raise StreamIdleTimeout(
                    f"No response from reviewer for {IDLE_TIMEOUT_SECONDS // 60} minutes"
                )

            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        feedback_parts.append(block.text)
                        console.print(block.text)
                    elif hasattr(block, "name"):
                        console.print(f"\n  [dim]Tool: {block.name}[/dim]")

            elif isinstance(message, ResultMessage):
                if hasattr(message, "total_cost_usd") and message.total_cost_usd:
                    console.print(f"  [dim]Review cost: ${message.total_cost_usd:.4f}[/dim]")

    except StreamIdleTimeout:
        raise  # Let caller handle retry
    except Exception as exc:
        console.print(f"\n  [red]Reviewer agent error: {exc}[/red]")

    feedback = "\n".join(feedback_parts)
    approved = "VERDICT: APPROVED" in feedback

    return approved, feedback


# ---------------------------------------------------------------------------
# Single ontology generation
# ---------------------------------------------------------------------------


async def generate_ontology(
    md_path: Path,
    output_dir: Path,
    model: str = DEFAULT_MODEL,
    max_turns: int = DEFAULT_MAX_TURNS,
) -> OntologyResult:
    """Generate an ontology from a single Markdown file.

    Steps:
      1. Agent reads Markdown + generates JSON-LD, writes file
      2. Python validates structural correctness (rdflib, domain/range, labels)
      3. On structural failure: feed errors to agent, repeat
      4. Connectivity/sparsity check: if sparse, enrichment loop
      5. LLM reviewer (fresh agent) assesses coverage & quality
      6. If reviewer says NEEDS_IMPROVEMENT: feed feedback to generator, repeat 2-5
      7. Convert validated + reviewed JSON-LD to OWL/RDF-XML
    """
    # Derive paths and metadata
    stem = md_path.stem
    namespace = derive_namespace(md_path.name)
    line_count = count_lines(md_path)

    json_dir = output_dir / "ontology_json"
    json_dir.mkdir(parents=True, exist_ok=True)
    json_path = json_dir / f"{stem}.json"
    owl_path = output_dir / f"{stem}.owl"

    console.rule(f"[bold]Generating ontology: {md_path.name}[/bold]")
    console.print(f"  Source:     {md_path}")
    console.print(f"  Output:     {json_path}")
    console.print(f"  Namespace:  {namespace}")
    console.print(f"  Lines:      {line_count:,}")
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
    # Phase 2 & 3: Structural validation loop
    # ------------------------------------------------------------------
    for attempt in range(1, MAX_VALIDATION_ATTEMPTS + 1):
        console.print(f"\n{'─' * 50}")
        console.print(
            f"[bold]Validation attempt {attempt}/{MAX_VALIDATION_ATTEMPTS}[/bold]"
        )
        console.print(f"{'─' * 50}")

        result = validate_ontology(json_path=json_path)

        if result.success:
            console.print(f"\n  [green]Structural validation passed![/green]")
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
                    result = validate_ontology(json_path=json_path)

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

            # ----------------------------------------------------------
            # Phase 4: LLM Review (fresh agent, clean context)
            # ----------------------------------------------------------
            review_approved, last_result = await _review_loop(
                json_path=json_path,
                md_path=md_path,
                connectivity_report=result.connectivity_report,
                model=model,
                max_turns=max_turns,
                session_id=session_id,
            )

            # If the review-fix cycle broke structural validation,
            # re-validate with the latest result
            if last_result is not None:
                result = last_result
                if not result.success:
                    # Fall through to the structural fix loop
                    continue

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


async def _review_loop(
    json_path: Path,
    md_path: Path,
    connectivity_report: str,
    model: str,
    max_turns: int,
    session_id: str | None,
) -> tuple[bool, "ValidationResult | None"]:
    """Run the LLM review loop with progressive leniency.

    Returns
    -------
    (approved, last_validation_result)
        approved: True if the reviewer approved (or max attempts exhausted).
        last_validation_result: the most recent ValidationResult if the
            review-fix cycle triggered re-validation, or None if no
            re-validation was needed (i.e., approved on first try).
    """
    from ontology_engine.models import ValidationResult  # avoid circular at module level

    previous_feedback: str | None = None
    last_result: ValidationResult | None = None

    for review_attempt in range(1, MAX_REVIEW_ATTEMPTS + 1):
        console.print(f"\n{'─' * 50}")
        console.print(
            f"[bold]LLM Review attempt {review_attempt}/{MAX_REVIEW_ATTEMPTS}[/bold]"
        )
        console.print(f"{'─' * 50}\n")

        review_prompt = build_review_prompt(
            json_path=json_path,
            md_path=md_path,
            connectivity_report=connectivity_report,
            attempt=review_attempt,
            max_attempts=MAX_REVIEW_ATTEMPTS,
            previous_feedback=previous_feedback,
        )

        approved, feedback = await _run_review(
            prompt=review_prompt,
            model=model,
        )

        if approved:
            console.print(f"\n  [green]Reviewer approved the ontology![/green]")
            return True, last_result

        console.print(f"\n  [yellow]Reviewer requested improvements.[/yellow]")
        previous_feedback = feedback

        if review_attempt == MAX_REVIEW_ATTEMPTS:
            console.print(
                f"\n  [yellow]Exhausted {MAX_REVIEW_ATTEMPTS} review attempts "
                f"— accepting ontology as-is.[/yellow]"
            )
            return True, last_result

        # Feed reviewer feedback to the generator agent
        console.print(
            f"\n[bold]Phase 4b:[/bold] Feeding reviewer feedback to generator "
            f"(cycle {review_attempt})...\n"
        )

        feedback_prompt = build_review_feedback_prompt(
            output_path=json_path,
            review_feedback=feedback,
            attempt=review_attempt,
        )

        fix_ok, session_id = await _run_agent(
            prompt=feedback_prompt,
            options=_agent_options(
                model=model,
                max_turns=max_turns,
                session_id=session_id,
            ),
        )

        # Re-validate structural correctness after the generator made changes
        last_result = validate_ontology(json_path=json_path)

        if not last_result.success:
            console.print(
                f"  [red]Review feedback fixes broke structural validation — "
                f"returning to fix loop.[/red]"
            )
            return False, last_result

        # Update connectivity report for the next review iteration
        connectivity_report = last_result.connectivity_report

    return True, last_result


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
