"""
JSON-LD to OWL/RDF-XML converter.

Uses rdflib to parse the validated JSON-LD and serialize to RDF/XML (OWL).
FR-006: 2-second delay between format generations.
"""

import json
import time
from pathlib import Path

from rdflib import Graph

from ontology_engine.utils import console


def convert_to_owl(json_path: Path, owl_path: Path) -> None:
    """Convert a validated JSON-LD ontology to OWL/RDF-XML format.

    Parameters
    ----------
    json_path:
        Path to the source JSON-LD file (must already be validated).
    owl_path:
        Path to write the OWL/RDF-XML output.

    Raises
    ------
    FileNotFoundError:
        If json_path does not exist.
    Exception:
        If rdflib fails to parse or serialize.
    """
    if not json_path.exists():
        raise FileNotFoundError(f"JSON-LD file not found: {json_path}")

    console.print(f"  Converting JSON-LD to OWL/RDF-XML...")

    # FR-006: 2-second delay between format generations
    # (JSON-LD was generated first by the agent, now we produce OWL)
    time.sleep(2)

    with open(json_path, encoding="utf-8") as f:
        data = json.load(f)

    graph = Graph()
    graph.parse(data=json.dumps(data), format="json-ld")

    # Ensure output directory exists
    owl_path.parent.mkdir(parents=True, exist_ok=True)

    graph.serialize(destination=str(owl_path), format="xml")
    console.print(f"  OWL/RDF-XML written to: {owl_path}")
