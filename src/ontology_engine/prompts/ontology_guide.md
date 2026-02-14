# JSON-LD OWL Ontology Format Reference

This document defines the exact format for OWL ontologies encoded as JSON-LD. Follow this specification precisely.

## Top-Level Structure

```json
{
  "@context": {
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "ns": "http://memebu.com/ontology/{namespace}#"
  },
  "@graph": [
    // ... all entities go here
  ]
}
```

- Replace `{namespace}` with the namespace provided to you.
- The `@graph` array contains ALL entities: classes, properties, and individuals.

## Entity Types

### 1. Classes (`owl:Class`)

Classes represent abstract concepts and categories in the domain.

```json
{
  "@id": "ns:ConceptName",
  "@type": "owl:Class",
  "rdfs:label": "Human Readable Name",
  "rdfs:comment": "Detailed description of this concept. Should be 2-3 sentences minimum, providing meaningful context about what this class represents in the domain."
}
```

With a superclass (for taxonomic hierarchies):

```json
{
  "@id": "ns:SpecificConcept",
  "@type": "owl:Class",
  "rdfs:label": "Specific Concept",
  "rdfs:comment": "Description of this more specific concept. Explain how it differs from its parent class and what distinguishes it.",
  "rdfs:subClassOf": { "@id": "ns:GeneralConcept" }
}
```

### 2. Object Properties (`owl:ObjectProperty`)

Object properties describe relationships between two classes.

```json
{
  "@id": "ns:relatesTo",
  "@type": "owl:ObjectProperty",
  "rdfs:label": "relates to",
  "rdfs:comment": "Describes the relationship between the domain and range classes. Should be 2-3 sentences explaining when and how this relationship applies.",
  "rdfs:domain": { "@id": "ns:DomainClass" },
  "rdfs:range": { "@id": "ns:RangeClass" }
}
```

**CRITICAL**: Every object property MUST have both `rdfs:domain` and `rdfs:range`.

### 3. Data Properties (`owl:DatatypeProperty`)

Data properties describe attributes of a class with a scalar value.

```json
{
  "@id": "ns:hasValue",
  "@type": "owl:DatatypeProperty",
  "rdfs:label": "has value",
  "rdfs:comment": "Description of what this attribute measures or represents. Include units if applicable.",
  "rdfs:domain": { "@id": "ns:SomeClass" },
  "rdfs:range": { "@id": "xsd:float" }
}
```

**CRITICAL**: Every data property MUST have both `rdfs:domain` and `rdfs:range`.

Common XSD range types: `xsd:string`, `xsd:float`, `xsd:integer`, `xsd:boolean`, `xsd:dateTime`.

### 4. Named Individuals (`owl:NamedIndividual`)

Individuals are specific instances of classes.

```json
{
  "@id": "ns:SpecificInstance",
  "@type": ["owl:NamedIndividual", "ns:ParentClass"],
  "rdfs:label": "Specific Instance Name",
  "rdfs:comment": "Detailed description of this specific instance. Explain what makes it notable and its significance in the domain. Should be 2-3 sentences minimum."
}
```

**NOTE**: The `@type` for individuals is an ARRAY containing both `owl:NamedIndividual` and the class it belongs to.

## Naming Conventions

- **Class names**: PascalCase (e.g., `NeuralNetwork`, `ActivationFunction`)
- **Property names**: camelCase (e.g., `usesAlgorithm`, `hasLearningRate`)
- **Individual names**: PascalCase (e.g., `Backpropagation`, `AdamOptimizer`)
- **Labels**: Human-readable with spaces (e.g., "Neural Network", "uses algorithm")
- All `@id` values must be prefixed with `ns:`

## Quality Requirements

1. **Comments**: Every entity MUST have an `rdfs:comment` of at least 2-3 sentences.
2. **Labels**: Every entity MUST have an `rdfs:label`.
3. **Domain/Range**: Every property (object and data) MUST have `rdfs:domain` and `rdfs:range`.
4. **Hierarchies**: Build meaningful class hierarchies using `rdfs:subClassOf`.
5. **Coverage**: The ontology should comprehensively cover the source document's domain.
6. **Valid JSON**: The output must be valid, parseable JSON. Pay special attention to trailing commas and proper escaping.
