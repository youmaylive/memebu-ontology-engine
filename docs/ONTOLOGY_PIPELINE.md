# Ontology Pipeline Documentation

## Overview

The Ontology Pipeline converts Markdown documents into structured OWL ontologies. This is Step 2 of the course generation process.

---

## INPUT

| Property | Description |
|----------|-------------|
| **Type** | Markdown file (`.md`) |
| **Source** | Output from PDF-to-Markdown conversion (Step 1) |
| **Path** | `{run_dir}/{filename}.md` |
| **Content** | Technical document with headings, paragraphs, formulas, lists |

### Input Example
```
/output/20260213_185108_run_5_v0/ComputationalNeuroscience.md
```

---

## OUTPUT

Two ontology files are generated:

### 1. JSON-LD Format
| Property | Value |
|----------|-------|
| **Location** | `{run_dir}/ontology_json/{filename}.json` |
| **Format** | JSON-LD with OWL vocabulary |
| **Use Case** | Web-friendly, easy to parse programmatically |

### 2. OWL/RDF-XML Format
| Property | Value |
|----------|-------|
| **Location** | `{run_dir}/{filename}.owl` |
| **Format** | RDF/XML OWL |
| **Use Case** | Standard ontology format, compatible with Protégé |

### Output Structure

Both formats contain these elements:

| Element | Description | Example |
|---------|-------------|---------|
| **Classes** | Abstract concepts and types | `NeuralNetwork`, `ActivationFunction`, `BrainRegion` |
| **Object Properties** | Relationships between entities | `usesAlgorithm`, `connectsTo`, `influencedBy` |
| **Data Properties** | Quantitative attributes | `hasLearningRate`, `numberOfLayers`, `accuracy` |
| **Individuals** | Specific instances | `Backpropagation`, `ReLU`, `AdamOptimizer` |
| **Hierarchies** | Taxonomic relationships | `ReLU rdfs:subClassOf ActivationFunction` |

---

## FUNCTIONAL REQUIREMENTS

### FR-001: Dynamic Class Extraction
- **Requirement:** Extract minimum number of classes based on document size
- **Formula:** `min_classes = max(20, line_count / 100)`
- **Example:** 5000-line document → minimum 50 classes

### FR-002: Dynamic Property Extraction
- **Requirement:** Extract minimum number of properties based on class count
- **Formula:** `min_properties = max(15, class_count / 2)`
- **Example:** 50 classes → minimum 25 properties

### FR-003: Dynamic Individual Extraction
- **Requirement:** Extract minimum number of individuals based on document size
- **Formula:** `min_individuals = max(50, line_count / 50)`
- **Example:** 5000-line document → minimum 100 individuals

### FR-004: Property Domain and Range
- **Requirement:** All properties MUST have `rdfs:domain` and `rdfs:range` defined
- **Validation:** Properties without domain/range are considered incomplete

### FR-005: Entity Labels and Descriptions
- **Requirement:** All entities MUST have:
  - `rdfs:label` - Human-readable name
  - `rdfs:comment` - Detailed description (2-3 sentences minimum)

### FR-006: Dual Format Generation
- **Requirement:** Generate both JSON-LD and RDF/XML OWL formats
- **Order:** JSON-LD first, then RDF/XML
- **Delay:** 2-second pause between generations

### FR-007: Large Document Handling
- **Requirement:** Handle documents >200,000 characters gracefully
- **Behavior:** Log warning, continue processing with extended timeout
- **Max Tokens:** 65,000 per LLM call

### FR-008: Namespace Derivation
- **Requirement:** Derive namespace from filename
- **Transformation:** Remove underscores and hyphens
- **Example:** `computational_neuroscience.md` → `computationalneuroscience`

---

## RESULT OBJECT

```python
OntologyResult(
    success: bool,              # True if generation succeeded
    json_path: Path,            # Path to JSON-LD file
    owl_path: Path,             # Path to OWL file
    namespace: str,             # Derived namespace
    stats: {
        "classes": int,         # Number of classes extracted
        "properties": int,      # Number of properties extracted
        "individuals": int      # Number of individuals extracted
    },
    error: Optional[str]        # Error message if failed
)
```

---

## CONFIGURATION

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `OPENROUTER_API_KEY` | API key for OpenRouter | Required |
| `OPENROUTER_API_BASE` | OpenRouter base URL | `https://openrouter.ai/api/v1` |
| `ONTOLOGY_MODEL` | LLM model for generation | Configured in settings |

---

## PIPELINE INTEGRATION

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Step 1: PDF    │────▶│  Step 2:        │────▶│  Step 3:        │
│  to Markdown    │     │  ONTOLOGY       │     │  Curriculum     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                              │
                              ▼
                        ┌─────────────┐
                        │  JSON-LD    │
                        │  + OWL      │
                        └─────────────┘
```
