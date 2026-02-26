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
MAX_VALIDATION_ATTEMPTS = 1    # Was 10 — reduced to prevent hours of loops on big files
MAX_CONTINUATION_ATTEMPTS = 0    # Was 3 — skip continuation (file is already on disk)
MAX_ENRICHMENT_ATTEMPTS = 0    # Was 2 — skip enrichment (unnecessary for curriculum)
MAX_REVIEW_ATTEMPTS = 0        # Was 3 — skip LLM review (unnecessary, saves time + cost)
