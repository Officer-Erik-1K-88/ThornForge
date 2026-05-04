"""ThornForge package marker."""

import email.utils
import importlib.metadata as importlib_metadata
from pathlib import Path
import tomllib


def _read_checkout_metadata() -> dict[str, str]:
    """Read enough project metadata for an uninstalled source checkout."""

    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = data.get("project", {})
    urls = project.get("urls", {})
    author = {}
    authors = project.get("authors", [])
    if authors:
        author = authors[0]
    return {
        "name": str(project.get("name", "thornforge")),
        "summary": str(project.get("description", "")),
        "homepage": str(urls.get("Homepage", "")),
        "version": "0+unknown",
        "author-email": email.utils.formataddr((str(author.get("name", "")), str(author.get("email", "")))),
    }


try:
    metadata = importlib_metadata.metadata("thornforge")
except importlib_metadata.PackageNotFoundError:
    checkout_metadata = _read_checkout_metadata()
    __title__ = checkout_metadata["name"]
    __summary__ = checkout_metadata["summary"]
    __uri__ = checkout_metadata["homepage"]
    __version__ = checkout_metadata["version"]
    __author__, __email__ = email.utils.parseaddr(checkout_metadata["author-email"])
else:
    __title__ = metadata["name"]
    __summary__ = metadata["summary"]
    __uri__ = next(
        entry.split(", ")[1]
        for entry in metadata.get_all("Project-URL", ())
        if entry.startswith("Homepage")
    )
    __version__ = metadata["version"]
    __author__, __email__ = email.utils.parseaddr(metadata["author-email"])
__license__ = None
