#!/usr/bin/env python3
"""
Translation Application Script

Applies optimized Chinese→English translations to files in the codebase.

Usage:
    python apply_translations.py

This script reads translations.json and applies the translations to all relevant files,
using the optimized prefix/suffix structure for accurate replacements.
"""

import json
import re
import os
from pathlib import Path

def load_blacklist(filepath='scan_blacklist.txt'):
    """
    Load directory exclusions from the blacklist file.

    Args:
        filepath: Path to the blacklist file

    Returns:
        set: Set of directory names to exclude
    """
    exclude_dirs = set()
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Strip trailing slashes to match directory names in path.parts
                    line = line.rstrip('/')
                    exclude_dirs.add(line)
    except FileNotFoundError:
        print(f"Warning: {filepath} not found, using default exclusions.")
        exclude_dirs = {'.git', 'node_modules', '__pycache__', '.vscode'}
    return exclude_dirs

def load_translations():
    """Load the optimized translations from translations.json."""
    try:
        with open('translations.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print("translations.json not found. Run extract_translations.py first.")
        return {}
    except json.JSONDecodeError as e:
        print(f"Error parsing translations.json: {e}")
        return {}

def reconstruct_full_translations(optimized_translations):
    """
    Reconstruct full string translations from optimized format.

    Returns:
        dict: Full Chinese -> English mappings
    """
    full_translations = {}

    for key, translations in optimized_translations.items():
        if '§' in key:
            parts = key.split('§', 1)
            prefix = parts[0]
            suffix = parts[1] if len(parts) > 1 else ""

            for chinese_middle, english_middle in translations.items():
                if chinese_middle or english_middle:  # Optimized translation
                    chinese_full = f"{prefix}{chinese_middle}{suffix}"
                    english_full = f"{prefix}{english_middle}{suffix}"
                    full_translations[chinese_full] = english_full
                else:  # Fallback full string
                    # This shouldn't happen with the new format, but handle it
                    pass
        else:
            # Legacy format handling
            pass

    return full_translations

def apply_translations_to_file(file_path, translations):
    """
    Apply translations to a single file.

    Args:
        file_path: Path to the file
        translations: Dict of Chinese -> English mappings

    Returns:
        bool: True if file was modified
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except (UnicodeDecodeError, OSError):
        # Skip binary files or files that can't be read
        return False

    original_content = content
    modified = False

    # Sort translations by length of Chinese text (longest first) to prevent
    # shorter matches from interfering with longer ones
    sorted_translations = sorted(translations.items(),
                               key=lambda x: len(x[0]), reverse=True)

    for chinese, english in sorted_translations:
        if chinese in content:
            content = content.replace(chinese, english)
            modified = True

    if modified and content != original_content:
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except OSError as e:
            print(f"Error writing to {file_path}: {e}")
            return False

    return False

def get_files_to_translate():
    """Get list of files that should be translated."""
    exclude_dirs = load_blacklist()
    exclude_files = {'extract_translations.py', 'apply_translations.py',
                    'translations.json', 'untranslated.txt'}

    files_to_translate = []

    for path in Path('.').rglob('*'):
        if path.is_file() and path.name not in exclude_files:
            # Get relative path and check exclusions
            rel_path = path.relative_to('.')
            rel_str = rel_path.as_posix()  # Use forward slashes for consistent checking
            if any(rel_str.startswith(excluded.rstrip('/')) for excluded in exclude_dirs):
                continue

            # Skip binary files
            if path.suffix in {'.jpg', '.png', '.gif', '.pdf', '.zip', '.pyc', '.exe'}:
                continue

            files_to_translate.append(path)

    return files_to_translate

def main():
    print("Loading translations...")
    optimized_translations = load_translations()

    if not optimized_translations:
        return

    print(f"Loaded {len(optimized_translations)} translation groups.")

    # Reconstruct full translations
    full_translations = reconstruct_full_translations(optimized_translations)
    print(f"Reconstructed {len(full_translations)} full translations.")

    # Get files to translate
    files_to_translate = get_files_to_translate()
    print(f"Found {len(files_to_translate)} files to process.")

    # Apply translations
    modified_count = 0
    for file_path in files_to_translate:
        if apply_translations_to_file(file_path, full_translations):
            modified_count += 1
            print(f"Modified: {file_path}")

    print(f"\nTranslation complete!")
    print(f"- Files modified: {modified_count}")
    print(f"- Files processed: {len(files_to_translate)}")

if __name__ == "__main__":
    main()
