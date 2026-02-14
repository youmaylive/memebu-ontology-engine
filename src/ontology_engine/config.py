"""
Shared configuration: paths and constants.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
ONTOLOGY_GUIDE = Path(__file__).resolve().parent / "prompts" / "ontology_guide.md"

# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------
DEFAULT_MODEL = "claude-sonnet-4-5"
DEFAULT_MAX_TURNS = 50
MAX_VALIDATION_ATTEMPTS = 10
MAX_CONTINUATION_ATTEMPTS = 3
MAX_ENRICHMENT_ATTEMPTS = 2
MAX_REVIEW_ATTEMPTS = 3
