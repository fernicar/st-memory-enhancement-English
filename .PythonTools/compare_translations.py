#!/usr/bin/env python3
"""
Compare translations.json with idealoutput.json and output the first 20 differences.
"""

import json

def load_json(filepath):
    """Load JSON from file."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def compare_dicts(d1, d2, path=""):
    """Recursively compare two dictionaries and return list of differences."""
    differences = []
    keys1 = set(d1.keys())
    keys2 = set(d2.keys())

    # Keys in d1 but not in d2
    for key in keys1 - keys2:
        differences.append(f"Key '{path}.{key}' in idealoutput.json but not in translations.json")

    # Keys in d2 but not in d1
    for key in keys2 - keys1:
        differences.append(f"Key '{path}.{key}' in translations.json but not in idealoutput.json")

    # Common keys
    for key in keys1 & keys2:
        if isinstance(d1[key], dict) and isinstance(d2[key], dict):
            differences.extend(compare_dicts(d1[key], d2[key], f"{path}.{key}"))
        elif d1[key] != d2[key]:
            differences.append(f"Value differs for '{path}.{key}': idealoutput.json='{d1[key]}' vs translations.json='{d2[key]}'")

    return differences

def main():
    try:
        translations = load_json('translations.json')
        idealoutput = load_json('idealoutput.json')
    except FileNotFoundError as e:
        print(f"Error: {e}")
        return

    differences = compare_dicts(idealoutput, translations)

    print(f"Total differences: {len(differences)}")
    print("First 20 differences:")
    for i, diff in enumerate(differences[:20]):
        print(f"{i+1}. {diff}")

if __name__ == "__main__":
    main()
