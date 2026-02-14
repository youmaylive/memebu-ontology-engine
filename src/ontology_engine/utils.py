"""
Utility helpers: namespace derivation and line counting.
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
