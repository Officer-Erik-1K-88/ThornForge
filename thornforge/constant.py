from pathlib import Path

DOC_INPUT_PATHS = (
    "docs",
    "piethorn",
    "pythorn",
    "README.rst",
    "pyproject.toml",
    "setup.py",
    "requirements.txt",
)

INJECTED_CONF_MARKER = "# Injected by scripts/build_versioned_docs.py"
INFO_RENDERED_SUFFIXES = {".rst", ".txt"}
SHARED_NAV_RELATIVE_PATHS = (
    Path("docs/_static/custom.css"),
    Path("docs/_static/top-nav.js"),
    Path("docs/_static/version-switcher.js"),
    Path("docs/_templates/versions.html"),
)
PROJECT_SITE_PAGES = (
    (Path("CHANGELOG.rst"), Path("changelog.html")),
)


def build_site_nav_stylesheet_href(root_prefix: str) -> str:
    return f"{root_prefix}_static/site-nav.css"


def build_site_nav_script_src(root_prefix: str) -> str:
    return f"{root_prefix}_static/top-nav.js"