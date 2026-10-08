"""README.md links must be absolute.

README.md is the package's long description, so PyPI renders it too. PyPI
resolves a relative link against pypi.org/project/<name>/, where no repository
file exists, so every relative link is dead there. Links into this repository
are absolute GitHub URLs, and each one names a file that exists.
"""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
README = (ROOT / "README.md").read_text(encoding="utf-8")
REPO = "https://github.com/scorched-earth-labs/astp-docs-core/"
LINK = re.compile(r"\]\(([^)\s]+)\)|href=\"([^\"]+)\"|src=\"([^\"]+)\"")


def _links():
    return [next(g for g in m.groups() if g) for m in LINK.finditer(README)]


def test_readme_has_no_relative_links():
    relative = [l for l in _links() if not re.match(r"(https?:|mailto:|#)", l)]
    assert relative == [], f"relative links render as 404s on PyPI: {relative}"


def test_readme_repository_links_name_existing_files():
    missing = []
    for link in _links():
        if not link.startswith(REPO):
            continue
        rest = link[len(REPO):].split("#")[0]
        kind, _, path = rest.partition("/main/")
        if kind not in ("blob", "tree") or not path:
            continue
        target = ROOT / path.rstrip("/")
        if not (target.is_dir() if kind == "tree" else target.is_file()):
            missing.append(link)
    assert missing == [], f"README links to paths that do not exist: {missing}"
