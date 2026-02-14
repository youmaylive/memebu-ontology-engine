"""
User prompt for fixing validation errors and enriching sparse ontologies.

Sent to the agent when the external validator detects errors in the
generated JSON-LD ontology file, or when the connectivity analysis
indicates the graph is too sparse.
"""

from pathlib import Path


def build_fix_prompt(output_path: Path, validation_errors: str, attempt: int) -> str:
    """Build a prompt that gives the agent validation errors to fix.

    Parameters
    ----------
    output_path:
        Path to the JSON-LD file that failed validation.
    validation_errors:
        Raw output from the validator (error messages).
    attempt:
        Current fix attempt number (1-indexed).
    """
    return f"""The JSON-LD ontology file you generated failed validation (attempt {attempt}).

**File**: {output_path}

**Validation errors**:
```
{validation_errors}
```

Read the error messages carefully, then edit the file to fix every error.
Make sure the JSON is valid and all entities meet the requirements.
After making your fixes, confirm that you are done."""


def build_enrichment_prompt(output_path: Path, connectivity_report: str) -> str:
    """Build a prompt that asks the agent to enrich a sparse ontology.

    Parameters
    ----------
    output_path:
        Path to the JSON-LD file that passed validation but is sparse.
    connectivity_report:
        Agent-readable connectivity analysis from the validator.
    """
    return f"""The JSON-LD ontology file passed validation but the graph connectivity
analysis shows it is too sparse and could be improved.

**File**: {output_path}

**Connectivity analysis**:
```
{connectivity_report}
```

Read the analysis carefully. Your goal is to **enrich** the ontology by adding
meaningful object properties that create cross-cutting relationships between
classes that are currently only connected through the subClassOf hierarchy.

Guidelines:
- Focus on classes listed as "taxonomy-only" or in disconnected components.
- Add object properties with proper rdfs:domain, rdfs:range, rdfs:label, and
  rdfs:comment.
- Do NOT remove existing content — only add new relationships.
- Each new property should capture a genuine semantic relationship from the
  source material (e.g., "isRegulatedBy", "participatesIn", "dependsOn").
- Aim to bring property coverage above 50% and reduce taxonomy-only classes.

After making your additions, confirm that you are done."""


def build_review_feedback_prompt(
    output_path: Path,
    review_feedback: str,
    attempt: int,
) -> str:
    """Build a prompt that feeds LLM reviewer feedback to the generator agent.

    Parameters
    ----------
    output_path:
        Path to the JSON-LD file to improve.
    review_feedback:
        Natural language feedback from the reviewer agent.
    attempt:
        Current review-fix cycle number (1-indexed).
    """
    return f"""A separate reviewer agent has analyzed the ontology you generated and
found areas for improvement (review cycle {attempt}).

**File**: {output_path}

**Reviewer feedback**:
```
{review_feedback}
```

Read the feedback carefully, then edit the ontology file to address the issues.

Guidelines:
- Focus on the specific issues listed above.
- Do NOT remove existing content — add or improve as needed.
- Ensure the JSON remains valid after your edits.
- Every new entity needs `rdfs:label` and `rdfs:comment`.
- Every new property needs `rdfs:domain` and `rdfs:range`.

After making your improvements, confirm that you are done."""


def build_continuation_prompt(output_path: Path) -> str:
    """Build a prompt to continue after a non-success agent session.

    Used when the agent session ends without success (e.g. token overflow,
    max turns reached). The agent is asked to check and complete the file.
    """
    return f"""Your previous session ended before confirming completion.

**Output file**: {output_path}

Please check if the JSON-LD ontology file exists and is complete:
1. If the file exists, read it to check if it is valid JSON with a complete `@graph` array
2. If incomplete or missing, generate and write the complete JSON-LD file
3. Confirm that you are done once the file is complete and valid"""
