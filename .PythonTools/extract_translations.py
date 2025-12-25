#!/usr/bin/env python3
"""
Translation Extraction Script

Extracts Chinese→English translation mappings from git staged changes
and identifies remaining untranslated Chinese text in the codebase.

Usage:
    python extract_translations.py

Output:
    - translations.json: Complete translation dictionary
"""

import subprocess
import json
import re
import os
from pathlib import Path

def find_common_prefix_suffix(str1, str2):
    """
    Find the longest common prefix and suffix between two strings.

    Returns:
        tuple: (prefix, suffix, middle1, middle2)
    """
    if not str1 or not str2:
        return "", "", str1, str2

    # Find common prefix
    prefix_len = 0
    min_len = min(len(str1), len(str2))
    while prefix_len < min_len and str1[prefix_len] == str2[prefix_len]:
        prefix_len += 1
    prefix = str1[:prefix_len]

    # Find common suffix
    suffix_len = 0
    while suffix_len < min_len - prefix_len and str1[-(suffix_len+1)] == str2[-(suffix_len+1)]:
        suffix_len += 1
    suffix = str1[-suffix_len:] if suffix_len > 0 else ""

    # Extract middle parts
    middle1 = str1[prefix_len:len(str1)-suffix_len]
    middle2 = str2[prefix_len:len(str2)-suffix_len]

    return prefix, suffix, middle1, middle2

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

def run_git_diff_staged():
    """Run git diff --staged and return the output."""
    try:
        result = subprocess.run(['git', 'diff', '--staged'],
                              capture_output=True, text=True, encoding='utf-8')
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error running git diff --staged: {e}")
        return ""



def parse_git_diff(diff_output):
    """
    Parse git diff output to extract Chinese→English mappings grouped by filename.

    Returns:
        dict: Dictionary mapping filenames to their translation dictionaries
    """
    raw_translations = {}

    # Split diff into individual file diffs
    file_diffs = re.split(r'^diff --git', diff_output, flags=re.MULTILINE)[1:]

    for file_diff in file_diffs:
        lines = file_diff.split('\n')
        first_line = lines[0]
        match = re.match(r' a/(.+) b/\1', first_line)
        if not match:
            continue
        filename = match.group(1).replace('/', '\\')
        file_translations = {}

        # Split into hunks (@@ ... @@)
        hunks = re.split(r'^@@', file_diff, flags=re.MULTILINE)[1:]

        for hunk in hunks:
            lines = hunk.strip().split('\n')

            # Collect removed and added lines
            removed = []
            added = []
            for line in lines:
                line = line.strip()
                if line.startswith('-'):
                    removed.append(line[1:].strip())
                elif line.startswith('+'):
                    added.append(line[1:].strip())

            # Pair removed and added lines by index from the end
            for i in range(min(len(removed), len(added))):
                old_text = clean_text(removed[len(removed) - 1 - i])
                new_text = clean_text(added[len(added) - 1 - i])

                # Only include if old_text contains Chinese and new_text doesn't
                if contains_chinese(old_text) and not contains_chinese(new_text) and old_text and new_text:
                    # Remove common prefix and suffix
                    prefix, suffix, middle1, middle2 = find_common_prefix_suffix(old_text, new_text)
                    if middle1 and middle2:
                        file_translations[middle1] = middle2

        if file_translations:
            raw_translations[filename] = file_translations

    return raw_translations

def contains_chinese(text):
    """Check if text contains Chinese characters."""
    # Match CJK Unified Ideographs (common Chinese characters)
    chinese_pattern = re.compile(r'[\u4e00-\u9fff]')
    return bool(chinese_pattern.search(text))

def clean_text(text):
    """Clean up text by removing surrounding quotes and extra whitespace."""
    text = text.strip()
    # Remove surrounding quotes if they match
    if (text.startswith('"') and text.endswith('"')) or \
       (text.startswith("'") and text.endswith("'")):
        text = text[1:-1]
    return text.strip()

def scan_codebase_for_chinese(root_path, exclude_dirs=None):
    """
    Scan the codebase for Chinese text.

    Args:
        root_path: Root directory to scan
        exclude_dirs: List of directory names to exclude

    Returns:
        dict: Dictionary mapping filenames to sets of Chinese phrases found in each file
    """
    if exclude_dirs is None:
        exclude_dirs = load_blacklist()

    file_phrases = {}

    for path in Path(root_path).rglob('*'):
        # Skip directories
        if path.is_dir():
            continue

        # Get relative path and check exclusions
        rel_path = path.relative_to(root_path)
        rel_str = rel_path.as_posix()  # Use forward slashes for consistent checking
        if any(rel_str.startswith(excluded.rstrip('/')) for excluded in exclude_dirs):
            continue

        # Skip binary files and certain extensions
        if path.suffix in {'.jpg', '.png', '.gif', '.pdf', '.zip', '.pyc'}:
            continue

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

                # Find all Chinese-containing lines
                lines = content.split('\n')
                phrases_in_file = set()
                for line in lines:
                    # Extract Chinese phrases from the line
                    phrases = extract_chinese_phrases(line)
                    phrases_in_file.update(phrases)

                if phrases_in_file:
                    file_phrases[str(path)] = phrases_in_file

        except Exception as e:
            # Skip files that can't be read
            continue

    return file_phrases

def extract_chinese_phrases(text):
    """Extract Chinese phrases from text."""
    phrases = set()

    # Find sequences of Chinese characters
    chinese_matches = re.findall(r'[\u4e00-\u9fff]+(?:[^\u4e00-\u9fff]*[\u4e00-\u9fff]+)*', text)

    for match in chinese_matches:
        # Clean up the phrase
        phrase = match.strip()
        if len(phrase) > 1:  # Only include phrases with 2+ characters
            phrases.add(phrase)

    return phrases

def main():
    print("Extracting translations from git staged changes...")

    # Get git diff output
    diff_output = run_git_diff_staged()
    if not diff_output:
        print("No staged changes found.")
        return

    # Parse translations from diff
    translations = parse_git_diff(diff_output)
    total_translations = sum(len(v) for v in translations.values())
    print(f"Found {total_translations} translations from staged changes.")

    # Scan codebase for remaining Chinese text
    print("Scanning codebase for remaining Chinese text...")
    file_phrases = scan_codebase_for_chinese('.')

    # Collect all phrases and track files per phrase
    all_chinese_phrases = set()
    phrase_files = {}  # phrase -> set of files
    for file_path, phrases in file_phrases.items():
        for phrase in phrases:
            all_chinese_phrases.add(phrase)
            if phrase not in phrase_files:
                phrase_files[phrase] = set()
            phrase_files[phrase].add(file_path)

    # Separate translated and untranslated
    translated_phrases = set()
    untranslated_phrases = set()

    for phrase in all_chinese_phrases:
        if any(phrase in file_trans for file_trans in translations.values()):
            translated_phrases.add(phrase)
        else:
            untranslated_phrases.add(phrase)

    # Find files with untranslated phrases
    files_with_untranslated = set()
    for file_path, phrases in file_phrases.items():
        if any(phrase in untranslated_phrases for phrase in phrases):
            files_with_untranslated.add(file_path)

    print(f"Found {len(translated_phrases)} translated Chinese phrases in codebase.")
    print(f"Found {len(untranslated_phrases)} untranslated Chinese phrases in codebase.")
    print(f"Files containing untranslated Chinese phrases:")
    for file_path in sorted(files_with_untranslated):
        print(f"  - {file_path}")

    # Save translations to JSON
    with open('translations.json', 'w', encoding='utf-8') as f:
        json.dump(translations, f, ensure_ascii=False, indent=2)

    print("Translation extraction complete!")
    print("- translations.json: Saved complete translation dictionary")
    print(f"- Translations extracted from git diff: {total_translations}")
    print(f"- Translated phrases in codebase: {len(translated_phrases)}")
    print(f"- Untranslated phrases in codebase: {len(untranslated_phrases)}")

if __name__ == "__main__":
    main()
