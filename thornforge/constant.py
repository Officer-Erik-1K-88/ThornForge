from pathlib import Path

INJECTED_CONF_MARKER = "# Injected by thornforge/build_versioned_docs.py"
INFO_RENDERED_SUFFIXES = {".rst", ".txt"}
TOOL_ROOT = Path(__file__).resolve().parents[1]
ASSET_ROOT = TOOL_ROOT / "assets"
HTML_TEMPLATE_ROOT = ASSET_ROOT / "templates" / "html"
SHARED_CSS_ASSET_PATHS = (
    Path("style/variables.css"),
    Path("style/style.css"),
    Path("style/nav.css"),
    Path("style/version.css"),
)
TOP_NAV_SCRIPT_ASSET_PATH = Path("scripts/top-nav.js")
VERSION_SWITCHER_SCRIPT_ASSET_PATH = Path("scripts/version-switcher.js")
VERSIONS_TEMPLATE_ASSET_PATH = Path("templates/html/versions.html")
PROJECT_PAGE_CANDIDATES = (
    ("README.rst", "readme.html"),
    ("README.txt", "readme.html"),
    ("README.html", "readme.html"),
    ("CHANGELOG.rst", "changelog.html"),
    ("CHANGELOG.txt", "changelog.html"),
    ("CHANGELOG.html", "changelog.html"),
    ("HISTORY.rst", "history.html"),
    ("HISTORY.txt", "history.html"),
    ("HISTORY.html", "history.html"),
    ("RELEASES.rst", "releases.html"),
    ("RELEASES.txt", "releases.html"),
    ("RELEASES.html", "releases.html"),
)
METADATA_CANDIDATES = (
    "info",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "requirements.txt",
    "package.json",
    "README.rst",
    "README.txt",
    "README.md",
    "CHANGELOG.rst",
    "CHANGELOG.txt",
    "CHANGELOG.md",
)

def build_stylesheet_hrefs(root_prefix: str) -> list[str]:
    return [f"{root_prefix}assets/{path.as_posix()}" for path in SHARED_CSS_ASSET_PATHS]


def build_site_nav_script_src(root_prefix: str) -> str:
    return f"{root_prefix}assets/{TOP_NAV_SCRIPT_ASSET_PATH.as_posix()}"


def build_version_switcher_script_src(root_prefix: str) -> str:
    return f"{root_prefix}assets/{VERSION_SWITCHER_SCRIPT_ASSET_PATH.as_posix()}"


def load_html_template(template_name: str) -> str:
    return (HTML_TEMPLATE_ROOT / template_name).read_text(encoding="utf-8")
