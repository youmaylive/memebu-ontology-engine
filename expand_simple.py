#!/usr/bin/env python3
import json

input_file = "/Users/elvish/Documents/CODING/memebu-ontology-engine/data/20260213_185108_run_5_v0/ontology_json/20260213_185106_Computational.Neuroscience-A.Comprehensive.Approach.json"

with open(input_file, 'r') as f:
    ontology = json.load(f)

graph = ontology['@graph']

# Count current entities
classes = [x for x in graph if x.get('@type') == 'owl:Class']
individuals = [x for x in graph if isinstance(x.get('@type'), list) and 'owl:NamedIndividual' in x['@type']]
obj_props = [x for x in graph if x.get('@type') == 'owl:ObjectProperty']
data_props = [x for x in graph if x.get('@type') == 'owl:DatatypeProperty']

print(f"Current counts:")
print(f"  Classes: {len(classes)}")
print(f"  Individuals: {len(individuals)}")
print(f"  Object Properties: {len(obj_props)}")
print(f"  Data Properties: {len(data_props)}")
print(f"  Total Properties: {len(obj_props) + len(data_props)}")
