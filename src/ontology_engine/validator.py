"""
External ontology validator.

Validates JSON-LD ontology files using rdflib and structural checks.
This is the mechanically enforced validation — the agent cannot skip it.
"""

from __future__ import annotations

import json
from collections import defaultdict, deque
from pathlib import Path
from typing import Any

from rdflib import Graph, Namespace, RDF, RDFS, OWL, XSD
from rdflib.term import URIRef

from ontology_engine.models import ValidationResult


# ---------------------------------------------------------------------------
# Namespace constants
# ---------------------------------------------------------------------------
_OWL_CLASS = OWL.Class
_OWL_OBJECT_PROPERTY = OWL.ObjectProperty
_OWL_DATATYPE_PROPERTY = OWL.DatatypeProperty
_OWL_NAMED_INDIVIDUAL = OWL.NamedIndividual

# ---------------------------------------------------------------------------
# Connectivity thresholds
# ---------------------------------------------------------------------------
_MIN_PROPERTY_COVERAGE = 0.40   # at least 40% of classes in some property
_MIN_PROP_CLASS_RATIO = 0.40    # at least 0.4 object properties per class
_MAX_TAXONOMY_ONLY_RATIO = 0.65 # no more than 65% taxonomy-only classes


def _local_name(uri: URIRef) -> str:
    """Extract the local name from a URI (after # or last /)."""
    s = str(uri)
    return s.split("#")[-1] if "#" in s else s.split("/")[-1]


# ---------------------------------------------------------------------------
# Connectivity analysis
# ---------------------------------------------------------------------------


def _connectivity_metrics(
    graph: Graph,
    classes: set[URIRef],
    obj_props: set[URIRef],
    data_props: set[URIRef],
    individuals: set[URIRef],
) -> tuple[dict[str, Any], str]:
    """Compute graph connectivity metrics and build an agent-readable report.

    Returns
    -------
    (metrics, report)
        metrics: dict of raw numbers for programmatic threshold checks.
        report: natural language diagnostic string for the agent.
    """
    n_classes = len(classes)
    n_obj_props = len(obj_props)
    n_data_props = len(data_props)

    # -- Collect which classes appear in any object property domain/range ----
    classes_in_domain: set[URIRef] = set()
    classes_in_range: set[URIRef] = set()

    for prop in obj_props:
        for _, _, dom in graph.triples((prop, RDFS.domain, None)):
            if dom in classes:
                classes_in_domain.add(dom)
        for _, _, rng in graph.triples((prop, RDFS.range, None)):
            if rng in classes:
                classes_in_range.add(rng)

    classes_in_properties = classes_in_domain | classes_in_range
    property_coverage = len(classes_in_properties) / n_classes if n_classes else 0.0
    prop_class_ratio = n_obj_props / n_classes if n_classes else 0.0

    # -- Build undirected adjacency for connected-component analysis --------
    adjacency: dict[URIRef, set[URIRef]] = defaultdict(set)

    # subClassOf edges
    for child, _, parent in graph.triples((None, RDFS.subClassOf, None)):
        if child in classes and parent in classes:
            adjacency[child].add(parent)
            adjacency[parent].add(child)

    # Object property domain/range creates links between domain class and
    # range class (the property itself acts as a bridge).
    for prop in obj_props:
        domains = {o for _, _, o in graph.triples((prop, RDFS.domain, None)) if o in classes}
        ranges = {o for _, _, o in graph.triples((prop, RDFS.range, None)) if o in classes}
        for d in domains:
            for r in ranges:
                adjacency[d].add(r)
                adjacency[r].add(d)

    # Ensure every class is a node (even if isolated)
    for cls in classes:
        adjacency.setdefault(cls, set())

    # -- Connected components via BFS ---------------------------------------
    visited: set[URIRef] = set()
    components: list[set[URIRef]] = []

    for node in classes:
        if node in visited:
            continue
        component: set[URIRef] = set()
        queue = deque([node])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            for neighbor in adjacency[current]:
                if neighbor not in visited:
                    queue.append(neighbor)
        components.append(component)

    # -- Orphan classes: no edges at all ------------------------------------
    orphan_classes = [cls for cls in classes if not adjacency[cls]]

    # -- Taxonomy-only classes: connected via subClassOf but never in any
    #    object property domain or range ------------------------------------
    taxonomy_only = [
        cls for cls in classes
        if cls not in classes_in_properties and cls not in orphan_classes
    ]

    # -- Degree stats -------------------------------------------------------
    degrees = [len(adjacency[cls]) for cls in classes]
    avg_degree = sum(degrees) / n_classes if n_classes else 0.0

    # -- Assemble raw metrics -----------------------------------------------
    metrics: dict[str, Any] = {
        "orphan_classes": len(orphan_classes),
        "property_coverage": round(property_coverage, 3),
        "property_to_class_ratio": round(prop_class_ratio, 3),
        "connected_components": len(components),
        "avg_class_degree": round(avg_degree, 2),
        "taxonomy_only_classes": len(taxonomy_only),
        "is_sparse": (
            property_coverage < _MIN_PROPERTY_COVERAGE
            or prop_class_ratio < _MIN_PROP_CLASS_RATIO
            or len(taxonomy_only) / n_classes > _MAX_TAXONOMY_ONLY_RATIO
            if n_classes
            else False
        ),
    }

    # -- Build agent-readable report ----------------------------------------
    lines: list[str] = [
        "Graph Connectivity Analysis",
        "=" * 28,
        f"The ontology has {n_classes} classes, {n_obj_props} object properties, "
        f"and {n_data_props} datatype properties.",
        "",
    ]

    warnings: list[str] = []

    # Property coverage
    covered = len(classes_in_properties)
    uncovered = n_classes - covered
    pct = f"{property_coverage:.0%}"
    if property_coverage < _MIN_PROPERTY_COVERAGE:
        warnings.append(
            f"Property coverage is LOW: only {covered} of {n_classes} classes ({pct}) "
            f"appear in any object property's domain or range. The remaining {uncovered} "
            f"classes are only connected through the subClassOf hierarchy and have no "
            f"relational semantics."
        )

    # Property-to-class ratio
    if prop_class_ratio < _MIN_PROP_CLASS_RATIO:
        warnings.append(
            f"Property-to-class ratio is {prop_class_ratio:.2f} "
            f"({n_obj_props} properties / {n_classes} classes). A well-connected ontology "
            f"typically has at least {_MIN_PROP_CLASS_RATIO} properties per class."
        )

    # Connected components
    if len(components) > 1:
        component_summaries = []
        for i, comp in enumerate(sorted(components, key=len, reverse=True), 1):
            names = sorted(_local_name(c) for c in comp)
            preview = ", ".join(names[:5])
            if len(names) > 5:
                preview += f", ... ({len(names)} classes total)"
            component_summaries.append(f"  Component {i}: {preview}")
        warnings.append(
            f"The graph has {len(components)} disconnected components. The following "
            f"class groups are completely unconnected to each other:\n"
            + "\n".join(component_summaries)
        )

    # Orphan classes
    if orphan_classes:
        names = sorted(_local_name(c) for c in orphan_classes)
        preview = ", ".join(names[:10])
        if len(names) > 10:
            preview += f" (and {len(names) - 10} more)"
        warnings.append(
            f"{len(orphan_classes)} orphan class(es) have NO connections at all "
            f"(no subClassOf, no property references): {preview}"
        )

    # Taxonomy-only classes
    if n_classes and len(taxonomy_only) / n_classes > _MAX_TAXONOMY_ONLY_RATIO:
        names = sorted(_local_name(c) for c in taxonomy_only)
        preview = ", ".join(names[:10])
        if len(names) > 10:
            preview += f" (and {len(names) - 10} more)"
        warnings.append(
            f"{len(taxonomy_only)} classes ({len(taxonomy_only) / n_classes:.0%}) are "
            f"taxonomy-only — connected solely through subClassOf and never referenced "
            f"by any object property. Consider adding object properties that relate "
            f"these classes to others. Taxonomy-only classes: {preview}"
        )

    if warnings:
        lines.append("Sparsity warnings:")
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("All connectivity checks passed:")
        lines.append(f"- Property coverage: {covered} of {n_classes} classes ({pct}) "
                      f"appear in object property domain/range.")
        lines.append(f"- Property-to-class ratio: {prop_class_ratio:.2f} "
                      f"({n_obj_props}/{n_classes}).")
        lines.append(f"- The graph is fully connected ({len(components)} component).")
        if orphan_classes:
            lines.append(f"- {len(orphan_classes)} orphan class(es) detected.")
        else:
            lines.append("- No orphan classes detected.")
        tax_pct = f"{len(taxonomy_only) / n_classes:.0%}" if n_classes else "0%"
        lines.append(f"- {len(taxonomy_only)} taxonomy-only classes ({tax_pct}) "
                      f"— within acceptable range.")

    report = "\n".join(lines)
    return metrics, report


def validate_ontology(
    json_path: Path,
    min_classes: int,
    min_properties: int,
    min_individuals: int,
) -> ValidationResult:
    """Validate a JSON-LD ontology file against all functional requirements.

    Checks performed (in order):
      1. File exists and is valid JSON
      2. JSON-LD structure has @context and @graph
      3. Parseable by rdflib
      4. FR-001: minimum classes
      5. FR-002: minimum properties
      6. FR-003: minimum individuals
      7. FR-004: all properties have domain and range
      8. FR-005: all entities have label and comment

    Parameters
    ----------
    json_path:
        Path to the JSON-LD file.
    min_classes:
        Minimum number of owl:Class entities (FR-001).
    min_properties:
        Minimum number of properties (FR-002).
    min_individuals:
        Minimum number of owl:NamedIndividual entities (FR-003).

    Returns
    -------
    ValidationResult with success flag, human-readable errors, and stats.
    """
    errors: list[str] = []

    # ------------------------------------------------------------------
    # Check 1: File exists and is valid JSON
    # ------------------------------------------------------------------
    if not json_path.exists():
        return ValidationResult(
            success=False,
            raw_output=f"File not found: {json_path}",
            error_count=1,
        )

    try:
        with open(json_path, encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as exc:
        return ValidationResult(
            success=False,
            raw_output=f"Invalid JSON: {exc}",
            error_count=1,
        )

    # ------------------------------------------------------------------
    # Check 2: JSON-LD structure
    # ------------------------------------------------------------------
    if "@context" not in data:
        errors.append("Missing @context in JSON-LD root")
    if "@graph" not in data:
        errors.append("Missing @graph in JSON-LD root")
    if not isinstance(data.get("@graph"), list):
        errors.append("@graph must be a JSON array")

    if errors:
        return ValidationResult(
            success=False,
            raw_output="\n".join(errors),
            error_count=len(errors),
        )

    # ------------------------------------------------------------------
    # Check 3: Parseable by rdflib
    # ------------------------------------------------------------------
    graph = Graph()
    try:
        graph.parse(data=json.dumps(data), format="json-ld")
    except Exception as exc:
        return ValidationResult(
            success=False,
            raw_output=f"rdflib failed to parse JSON-LD: {exc}",
            error_count=1,
        )

    # ------------------------------------------------------------------
    # Count entities by type
    # ------------------------------------------------------------------
    classes = set(s for s, _, _ in graph.triples((None, RDF.type, _OWL_CLASS)))
    obj_props = set(s for s, _, _ in graph.triples((None, RDF.type, _OWL_OBJECT_PROPERTY)))
    data_props = set(s for s, _, _ in graph.triples((None, RDF.type, _OWL_DATATYPE_PROPERTY)))
    individuals = set(s for s, _, _ in graph.triples((None, RDF.type, _OWL_NAMED_INDIVIDUAL)))
    all_properties = obj_props | data_props

    stats = {
        "classes": len(classes),
        "object_properties": len(obj_props),
        "data_properties": len(data_props),
        "individuals": len(individuals),
    }

    # ------------------------------------------------------------------
    # Check 4: FR-001 — minimum classes
    # ------------------------------------------------------------------
    if len(classes) < min_classes:
        errors.append(
            f"FR-001: Too few classes: {len(classes)} found, minimum {min_classes} required"
        )

    # ------------------------------------------------------------------
    # Check 5: FR-002 — minimum properties
    # ------------------------------------------------------------------
    if len(all_properties) < min_properties:
        errors.append(
            f"FR-002: Too few properties: {len(all_properties)} found "
            f"(object: {len(obj_props)}, data: {len(data_props)}), "
            f"minimum {min_properties} required"
        )

    # ------------------------------------------------------------------
    # Check 6: FR-003 — minimum individuals
    # ------------------------------------------------------------------
    if len(individuals) < min_individuals:
        errors.append(
            f"FR-003: Too few individuals: {len(individuals)} found, "
            f"minimum {min_individuals} required"
        )

    # ------------------------------------------------------------------
    # Check 7: FR-004 — properties must have domain and range
    # ------------------------------------------------------------------
    props_missing_domain: list[str] = []
    props_missing_range: list[str] = []

    for prop in all_properties:
        has_domain = any(graph.triples((prop, RDFS.domain, None)))
        has_range = any(graph.triples((prop, RDFS.range, None)))
        if not has_domain:
            props_missing_domain.append(_local_name(prop))
        if not has_range:
            props_missing_range.append(_local_name(prop))

    if props_missing_domain:
        errors.append(
            f"FR-004: Properties missing rdfs:domain: {', '.join(props_missing_domain[:10])}"
            + (f" (and {len(props_missing_domain) - 10} more)" if len(props_missing_domain) > 10 else "")
        )
    if props_missing_range:
        errors.append(
            f"FR-004: Properties missing rdfs:range: {', '.join(props_missing_range[:10])}"
            + (f" (and {len(props_missing_range) - 10} more)" if len(props_missing_range) > 10 else "")
        )

    # ------------------------------------------------------------------
    # Check 8: FR-005 — entities must have label and comment
    # ------------------------------------------------------------------
    all_entities = classes | all_properties | individuals
    missing_label: list[str] = []
    missing_comment: list[str] = []

    for entity in all_entities:
        has_label = any(graph.triples((entity, RDFS.label, None)))
        has_comment = any(graph.triples((entity, RDFS.comment, None)))
        if not has_label:
            missing_label.append(_local_name(entity))
        if not has_comment:
            missing_comment.append(_local_name(entity))

    if missing_label:
        errors.append(
            f"FR-005: Entities missing rdfs:label: {', '.join(missing_label[:10])}"
            + (f" (and {len(missing_label) - 10} more)" if len(missing_label) > 10 else "")
        )
    if missing_comment:
        errors.append(
            f"FR-005: Entities missing rdfs:comment: {', '.join(missing_comment[:10])}"
            + (f" (and {len(missing_comment) - 10} more)" if len(missing_comment) > 10 else "")
        )

    # ------------------------------------------------------------------
    # Connectivity analysis (always run when we have a valid graph)
    # ------------------------------------------------------------------
    conn_metrics, conn_report = _connectivity_metrics(
        graph=graph,
        classes=classes,
        obj_props=obj_props,
        data_props=data_props,
        individuals=individuals,
    )

    # ------------------------------------------------------------------
    # Build result
    # ------------------------------------------------------------------
    if errors:
        header = (
            f"Validation failed with {len(errors)} error(s).\n"
            f"Stats: {stats['classes']} classes, "
            f"{stats['object_properties']} object properties, "
            f"{stats['data_properties']} data properties, "
            f"{stats['individuals']} individuals.\n"
        )
        return ValidationResult(
            success=False,
            raw_output=header + "\n".join(f"  - {e}" for e in errors),
            error_count=len(errors),
            stats=stats,
            connectivity=conn_metrics,
            connectivity_report=conn_report,
        )

    return ValidationResult(
        success=True,
        raw_output=(
            f"Validation passed. "
            f"{stats['classes']} classes, "
            f"{stats['object_properties']} object properties, "
            f"{stats['data_properties']} data properties, "
            f"{stats['individuals']} individuals."
        ),
        error_count=0,
        stats=stats,
        connectivity=conn_metrics,
        connectivity_report=conn_report,
    )
