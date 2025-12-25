import json
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

def compare_line_by_line_with_other_repo(other_repo_path=r'G:\st-memory-enhancement-master', english_root='.', exclude_dirs=None):
    """
    Compare line by line with another repository to extract translations.

    Args:
        other_repo_path: Path to the other repository
        english_root: Root directory of the English repository
        exclude_dirs: List of directory names to exclude

    Returns:
        dict: Dictionary grouped by filename containing translation mappings
    """
    if exclude_dirs is None:
        exclude_dirs = load_blacklist()

    translations = {}

    for path in Path(english_root).rglob('*'):
        # Skip directories
        if path.is_dir():
            continue

        # Get relative path and check exclusions
        rel_path = path.relative_to(english_root)
        rel_str = rel_path.as_posix()  # Use forward slashes for consistent checking
        if any(rel_str.startswith(excluded.rstrip('/')) for excluded in exclude_dirs):
            continue

        # Skip binary files and certain extensions
        if path.suffix in {'.jpg', '.png', '.gif', '.pdf', '.zip', '.pyc'}:
            continue

        other_path = Path(other_repo_path) / rel_path
        if not other_path.exists():
            continue

        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                english_content = f.read()
            with open(other_path, 'r', encoding='utf-8', errors='ignore') as f:
                other_content = f.read()

            english_lines = english_content.split('\n')
            other_lines = other_content.split('\n')

            # Assume matching line counts, compare line by line
            file_translations = {}
            for other_line, english_line in zip(other_lines, english_lines):
                if other_line != english_line:
                    prefix, suffix, middle_other, middle_english = find_common_prefix_suffix(other_line, english_line)
                    if middle_other and middle_english and middle_other != middle_english:
                        file_translations[middle_other] = middle_english

            if file_translations:
                translations[str(path)] = file_translations

        except Exception as e:
            # Skip files that can't be read
            continue

    return translations

def main():
    other_translations = compare_line_by_line_with_other_repo()

    # Save other translations to JSON
    with open('idealoutput.json', 'w', encoding='utf-8') as f:
        json.dump(other_translations, f, ensure_ascii=False, indent=2)
    print("- idealoutput.json: Translations from line-by-line comparison")
    # Print summary
    print(f"\nSummary:")
    print(f"- Files with translations from comparison: {len(other_translations)}")

if __name__ == "__main__":
    main()
