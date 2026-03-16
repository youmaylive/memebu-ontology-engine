"""
User prompt for the initial ontology generation step.

Supports both single-file and multi-file ontology generation.
"""

from pathlib import Path
from typing import Union


def build_generation_prompt(
    md_path: Union[Path, list[Path]],
    output_path: Path,
    namespace: str,
    line_count: int,
) -> str:
    """Build the user prompt that instructs the agent to generate a JSON-LD ontology.

    Args:
        md_path: Single Path or list of Paths to source markdown files.
        output_path: Where to write the JSON-LD output.
        namespace: Ontology namespace identifier.
        line_count: Total line count across all source files.
    """
    # Multi-file mode
    if isinstance(md_path, list) and len(md_path) > 1:
        return _build_multi_file_prompt(md_path, output_path, namespace, line_count)

    # Single-file mode (backward compatible)
    single_path = md_path[0] if isinstance(md_path, list) else md_path
    return _build_single_file_prompt(single_path, output_path, namespace, line_count)


def _build_single_file_prompt(
    md_path: Path,
    output_path: Path,
    namespace: str,
    line_count: int,
) -> str:
    """Original single-file prompt."""
    return f"""Generate an OWL ontology in JSON-LD format from the Markdown document.

**Source document**: {md_path}
**Output file path**: {output_path}
**Document size**: {line_count:,} lines
**Namespace**: {namespace}

The `@context.ns` value must be: `http://memebu.com/ontology/{namespace}#`

### Goal:
Extract a **comprehensive** ontology that captures all significant domain concepts,
relationships, attributes, and named instances from the source document. Be thorough
— the ontology will be reviewed for completeness and coverage against the source
material by a separate reviewer.

### Steps:
1. Read the source document: {md_path}
   - For large files, read in chunks using offset and limit parameters
2. Extract all domain concepts, relationships, attributes, and named instances
3. Generate a complete, valid JSON-LD ontology
4. Write the JSON-LD file to: {output_path}

### Reminders:
- Every entity needs `rdfs:label` and `rdfs:comment` (2-3 sentences)
- Every property needs `rdfs:domain` and `rdfs:range`
- Build meaningful class hierarchies with `rdfs:subClassOf`
- Create cross-cutting object properties — not just taxonomy (subClassOf) but
  relational connections between concepts (e.g., "uses", "regulatedBy", "locatedIn")
- Named individuals need `@type` as an array: `["owl:NamedIndividual", "ns:ClassName"]`
- The JSON must be valid — no trailing commas, proper bracket matching
- Use `bash` with heredoc (`cat >` / `cat >>`) to write the file — NOT the Write tool
- You may split across multiple bash calls if needed (first `cat >`, then `cat >>` to append)

Once you have written the file, confirm that you are done."""


def _build_multi_file_prompt(
    md_paths: list[Path],
    output_path: Path,
    namespace: str,
    total_line_count: int,
) -> str:
    """Multi-file prompt: read ALL source files and build ONE unified ontology."""
    files_list = "\n".join(f"  {i}. `{p}` ({p.name})" for i, p in enumerate(md_paths, 1))

    return f"""Generate a **single unified** OWL ontology in JSON-LD format from **multiple** source documents.

**Source documents** ({len(md_paths)} files):
{files_list}

**Output file path**: {output_path}
**Total document size**: {total_line_count:,} lines across {len(md_paths)} files
**Namespace**: {namespace}

The `@context.ns` value must be: `http://memebu.com/ontology/{namespace}#`

### Goal:
Read ALL {len(md_paths)} source documents and extract a **single, comprehensive, unified** ontology
that captures all significant domain concepts, relationships, attributes, and named
instances from **every** source file. Be thorough — the ontology will be reviewed for
completeness and coverage against ALL source materials by a separate reviewer.

**IMPORTANT — Multi-source rules:**
- Concepts that appear in multiple files should be represented as ONE class (not duplicated)
- Cross-reference relationships between concepts from different files
- If two files describe the same topic differently, merge the information into one richer entity
- Track which source files contributed to each concept using `rdfs:comment`

### Steps:
1. Read ALL source documents one by one:
{chr(10).join(f'   - Read: {p}' for p in md_paths)}
   - For large files, read in chunks using offset and limit parameters
2. Identify concepts across ALL files — merge duplicates, cross-reference related topics
3. Extract all domain concepts, relationships, attributes, and named instances
4. Generate a complete, valid JSON-LD ontology covering ALL sources
5. Write the JSON-LD file to: {output_path}

### Reminders:
- Every entity needs `rdfs:label` and `rdfs:comment` (2-3 sentences)
- Every property needs `rdfs:domain` and `rdfs:range`
- Build meaningful class hierarchies with `rdfs:subClassOf`
- Create cross-cutting object properties — not just taxonomy (subClassOf) but
  relational connections between concepts (e.g., "uses", "regulatedBy", "locatedIn")
- Named individuals need `@type` as an array: `["owl:NamedIndividual", "ns:ClassName"]`
- The JSON must be valid — no trailing commas, proper bracket matching
- Use `bash` with heredoc (`cat >` / `cat >>`) to write the file — NOT the Write tool
- You may split across multiple bash calls if needed (first `cat >`, then `cat >>` to append)

Once you have written the file, confirm that you are done."""
