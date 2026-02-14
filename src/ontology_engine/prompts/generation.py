"""
User prompt for the initial ontology generation step.
"""

from pathlib import Path


def build_generation_prompt(
    md_path: Path,
    output_path: Path,
    namespace: str,
    line_count: int,
) -> str:
    """Build the user prompt that instructs the agent to generate a JSON-LD ontology."""
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
