"""
Prompt for the LLM reviewer agent.

The reviewer is a fresh agent (clean context) that reads the ontology and
the source document, then provides qualitative feedback on coverage and
quality. Subsequent attempts scale leniency so the loop converges.
"""

from pathlib import Path


def build_review_prompt(
    json_path: Path,
    md_path: Path,
    connectivity_report: str,
    attempt: int,
    max_attempts: int,
    previous_feedback: str | None = None,
) -> str:
    """Build the prompt for the LLM reviewer agent.

    Parameters
    ----------
    json_path:
        Path to the JSON-LD ontology file to review.
    md_path:
        Path to the original Markdown source document.
    connectivity_report:
        Agent-readable connectivity analysis from the validator.
    attempt:
        Current review attempt number (1-indexed).
    max_attempts:
        Maximum number of review attempts (for context).
    previous_feedback:
        Feedback from the previous review attempt, if any.
    """
    leniency = _leniency_section(attempt, max_attempts, previous_feedback)

    return f"""You are an ontology quality reviewer. Your job is to assess whether
a JSON-LD ontology adequately captures the domain knowledge from a source document.

**Ontology file**: {json_path}
**Source document**: {md_path}

### Graph connectivity (already analyzed — do NOT repeat this analysis):
```
{connectivity_report}
```

{leniency}

### Review process:
1. Read the source document (skim for major topics, sections, and key concepts)
2. Read the ontology file
3. Compare: does the ontology capture the major topics from the source?

### What to evaluate:
- **Coverage**: Are the main topics and concepts from the source represented as classes?
- **Relationships**: Are there meaningful object properties beyond just subClassOf hierarchies?
- **Individuals**: Are specific named instances (algorithms, models, methods, etc.) captured?
- **Quality**: Are labels and comments informative and drawn from the source material?

### What NOT to evaluate (already handled separately):
- JSON validity and rdflib parseability (handled by structural validator)
- Domain/range completeness on properties (handled by structural validator)
- Graph sparsity metrics (handled by connectivity analysis above)

### Your verdict:
After your review, you MUST end your response with exactly one of:

**If the ontology is acceptable:**
```
VERDICT: APPROVED
```

**If the ontology needs improvement:**
```
VERDICT: NEEDS_IMPROVEMENT
- [specific issue 1]
- [specific issue 2]
- ...
```

Keep your issue list concise and actionable — each item should be something
the generator agent can fix in a single pass."""


def _leniency_section(
    attempt: int,
    max_attempts: int,
    previous_feedback: str | None,
) -> str:
    """Build the leniency instructions based on attempt number."""
    if attempt == 1:
        return """### Review standards (first review):
Be thorough. Identify significant gaps in coverage, missing relationships,
and quality issues. Focus on whether the ontology captures the **major**
topics and concepts from the source document — not every minor detail."""

    if attempt == 2:
        return f"""### Review standards (second review — be MORE lenient):
This is a second review after the generator addressed previous feedback.
The ontology has already been improved once.

**Previous feedback that was addressed:**
```
{previous_feedback or "(none)"}
```

Focus ONLY on the most important remaining issues. Minor gaps in coverage
are acceptable. If the ontology covers the major topics from the source
and has reasonable relationships, approve it."""

    # attempt >= 3
    return f"""### Review standards (attempt {attempt}/{max_attempts} — be VERY lenient):
This ontology has been reviewed and improved {attempt - 1} time(s) already.
Previous feedback:
```
{previous_feedback or "(none)"}
```

Only flag **critical** problems — such as entire major sections of the source
document being completely absent. If the ontology covers the core domain
concepts and has a reasonable structure, **approve it**.

Do NOT nitpick. The goal is convergence, not perfection."""
