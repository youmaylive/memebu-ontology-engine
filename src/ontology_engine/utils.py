"""
Utility helpers: namespace derivation, line counting, minimum computation.
"""

import re
from pathlib import Path

from rich.console import Console

console = Console()


def derive_namespace(filename: str) -> str:
    """Derive an ontology namespace from a filename.

    FR-008: Remove underscores, hyphens, dots, and periods; lowercase.

    Examples
    --------
    >>> derive_namespace("computational_neuroscience.md")
    'computationalneuroscience'
    >>> derive_namespace("20260213_185106_Computational.Neuroscience-A.Comprehensive.Approach.md")
    'computationalneuroscienceacomprehensiveapproach'
    """
    stem = Path(filename).stem
    # Strip leading timestamp prefix (e.g. "20260213_185106_")
    stem = re.sub(r"^\d{8}_\d{6}_", "", stem)
    # Remove underscores, hyphens, dots
    cleaned = re.sub(r"[_\-.]", "", stem)
    return cleaned.lower()


def count_lines(file_path: Path) -> int:
    """Count the number of lines in a text file."""
    with open(file_path, encoding="utf-8") as f:
        return sum(1 for _ in f)


def compute_minimums(line_count: int) -> dict[str, int]:
    """Compute minimum entity counts based on document size.

    Returns
    -------
    dict with keys: min_classes, min_properties, min_individuals
    """
    min_classes = max(20, line_count // 100)
    min_properties = max(15, min_classes // 2)
    min_individuals = max(50, line_count // 50)
    return {
        "min_classes": min_classes,
        "min_properties": min_properties,
        "min_individuals": min_individuals,
    }
