"""Print the CHANGELOG.md section for one version, for its GitHub Release.

    python3 .github/scripts/changelog_notes.py 0.1.0

Prints the body under ``## [0.1.0] ...`` up to the next ``## [`` heading,
without the link definitions (``[0.1.0]: https://...``) that end the file.
Falls back to a generic line if the version has no section.
"""

import re
import sys
from pathlib import Path

CHANGELOG = Path("CHANGELOG.md")
LINK_DEFINITION = re.compile(r"^\[[^\]]+\]:\s+\S+\s*$", re.MULTILINE)


def notes_for(version: str, text: str) -> str:
    pattern = re.compile(
        r"^##\s*\[" + re.escape(version) + r"\][^\n]*\n(.*?)(?=^##\s*\[|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    match = pattern.search(text)
    if match:
        body = LINK_DEFINITION.sub("", match.group(1)).strip()
        if body:
            return body
    return f"Release {version}."


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: changelog_notes.py <version>", file=sys.stderr)
        return 2
    text = CHANGELOG.read_text(encoding="utf-8") if CHANGELOG.exists() else ""
    print(notes_for(sys.argv[1], text))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
