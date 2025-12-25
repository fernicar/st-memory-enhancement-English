import json
import re
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
            print(f"\t can't read {e}")
            # Skip files that can't be read
            continue

    return file_phrases

def main():
    # Scan codebase for remaining Chinese text
    print("Scanning codebase for remaining Chinese text...")
    file_phrases = scan_codebase_for_chinese('.')

    # Collect all phrases and track files per phrase
    all_chinese_phrases = set()
    for file_path, phrases in file_phrases.items():
        for phrase in phrases:
            all_chinese_phrases.add(phrase)

    # Separate translated and untranslated
    untranslated_phrases = set()
    translations = {} # temp empty val

    for phrase in all_chinese_phrases:
        if any(phrase in file_trans for file_trans in translations.values()):
            continue
        else:
            untranslated_phrases.add(phrase)
    # Find files with untranslated phrases
    files_with_untranslated = set()
    for file_path, phrases in file_phrases.items():
        if any(phrase in untranslated_phrases for phrase in phrases):
            files_with_untranslated.add(file_path)

    print(f"Files containing untranslated Chinese phrases:")
    for file_path in sorted(files_with_untranslated):
        print(f"  - {file_path}")
        # for phrase in untranslated_phrases:
        #     print(f"   - {phrase}")
    print(f"- Untranslated phrases in codebase: {len(untranslated_phrases)}")

if __name__ == "__main__":
    main()
