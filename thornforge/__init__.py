"""ThornForge package marker."""

import email.utils
import importlib.metadata as importlib_metadata

metadata = importlib_metadata.metadata("thornforge")
assert metadata is not None  # nosec: B101


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