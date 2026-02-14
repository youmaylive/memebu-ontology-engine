"""
Data classes for the ontology pipeline.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ValidationResult:
    """Result of validating a JSON-LD ontology file."""

    success: bool
    """True if all checks passed."""

    raw_output: str
    """Human-readable error/success report."""

    error_count: int
    """Number of distinct errors detected."""

    stats: dict[str, int] = field(default_factory=dict)
    """Entity counts: classes, object_properties, data_properties, individuals."""

    connectivity: dict[str, Any] = field(default_factory=dict)
    """Raw connectivity metrics for programmatic threshold checks."""

    connectivity_report: str = ""
    """Agent-readable natural language connectivity analysis."""


@dataclass
class OntologyResult:
    """Result of generating an ontology from a single Markdown file."""

    success: bool
    """True if generation, validation, and conversion all succeeded."""

    json_path: Path | None = None
    """Path to the validated JSON-LD file."""

    owl_path: Path | None = None
    """Path to the generated OWL/RDF-XML file."""

    namespace: str = ""
    """Derived namespace string."""

    stats: dict[str, int] = field(default_factory=dict)
    """Entity counts: classes, object_properties, data_properties, individuals."""

    error: str | None = None
    """Error message if generation failed."""
