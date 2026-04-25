from __future__ import annotations
"""Helpers for copying and rendering the optional ``info/`` site subtree.

The ``info/`` directory is treated as a lightweight project website rooted at
the final site output. Text-based inputs can be rendered or wrapped as HTML,
while binary or unknown files are copied through unchanged.
"""

import html
from pathlib import Path
import shutil
from typing import Iterable

from thornforge.buildsite.constant import INFO_RENDERED_SUFFIXES
from thornforge.buildsite.nav import wrap_info_html_document


def iter_info_files(info_dir: Path) -> Iterable[Path]:
    """Yield files from ``info/`` in deterministic order.

    Args:
        info_dir: Root ``info/`` directory to scan recursively.

    Yields:
        File paths under ``info_dir`` sorted lexicographically.
    """

    for path in sorted(info_dir.rglob("*")):
        if path.is_file():
            # Only files become site outputs; directories are just traversal scaffolding.
            yield path


def info_output_relative_path(info_dir: Path, source_path: Path) -> Path:
    """Translate one ``info/`` source file into its published relative path.

    Args:
        info_dir: Root ``info/`` directory.
        source_path: File path beneath ``info_dir``.

    Returns:
        Relative output path under the final site. Text-like sources gain an
        ``.html`` suffix because they are rendered into HTML pages.
    """

    relative_path = source_path.relative_to(info_dir)
    if source_path.suffix.lower() in INFO_RENDERED_SUFFIXES:
        # Rendered text-like inputs become .html pages in the final site.
        return relative_path.with_suffix(".html")
    return relative_path


def root_prefix_for_output(output_relative_path: Path) -> str:
    """Return the relative prefix needed to address site-root assets.

    Args:
        output_relative_path: Page path relative to the site root.

    Returns:
        Empty string for root pages or a repeated ``../`` prefix that navigates
        from the page's parent directory back to the site root.
    """

    parent = output_relative_path.parent
    if str(parent) == ".":
        return ""
    # One ../ segment is needed for each directory level between the page and the site root.
    return "../" * len(parent.parts)


def render_rst_info_page(source_path: Path, destination: Path, root_prefix: str, current_path: str) -> None:
    """Render one reStructuredText ``info/`` file into wrapped HTML.

    Args:
        source_path: Input ``.rst`` file to render.
        destination: Output HTML path to write.
        root_prefix: Relative prefix from the destination page back to the site
            root, used for shared asset links.
        current_path: Site-relative path for the destination page, used by the
            navigation placeholder.

    Side Effects:
        Writes the rendered and wrapped HTML page to ``destination``.

    Returns:
        None.
    """

    from docutils.core import publish_parts

    source = source_path.read_text(encoding="utf-8")
    # Let docutils do the RST-to-HTML conversion before ThornForge adds its own shell.
    parts = publish_parts(source=source, writer_name="html5")
    title = parts.get("title", source_path.stem)
    body_html = parts.get("body") or parts.get("whole") or ""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        wrap_info_html_document(
            body_html,
            root_prefix,
            title=title,
            current_path=current_path,
        ),
        encoding="utf-8",
    )


def render_plain_text_info_page(source_path: Path, destination: Path, root_prefix: str, current_path: str) -> None:
    """Render a plain-text ``info/`` file into a wrapped HTML page.

    Args:
        source_path: Input text file to display.
        destination: Output HTML path to write.
        root_prefix: Relative prefix from the destination page back to the site
            root.
        current_path: Site-relative output path used by the shared navigation.

    Returns:
        None. The wrapped HTML page is written to ``destination``.
    """

    # Escape the text so it displays literally inside the generated HTML page.
    text = html.escape(source_path.read_text(encoding="utf-8"))
    title = source_path.stem
    body_html = f"<pre>{text}</pre>"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        wrap_info_html_document(
            body_html,
            root_prefix,
            title=title,
            current_path=current_path,
        ),
        encoding="utf-8",
    )


def inject_nav_into_html(source_path: Path, destination: Path, root_prefix: str, current_path: str) -> None:
    """Wrap an existing HTML document with ThornForge's shared layout shell.

    Args:
        source_path: Input HTML file whose content should be wrapped.
        destination: Output HTML path to write.
        root_prefix: Relative prefix from the destination page back to the site
            root.
        current_path: Site-relative output path used by the shared navigation.

    Returns:
        None. The wrapped document is written to ``destination``.
    """

    # Existing HTML is not re-rendered; ThornForge only wraps it with shared assets and nav.
    document = source_path.read_text(encoding="utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        wrap_info_html_document(
            document,
            root_prefix,
            title=source_path.stem,
            current_path=current_path,
        ),
        encoding="utf-8",
    )


def copy_info_site(repo_root: Path, output_dir: Path) -> bool:
    """Publish the optional ``info/`` subtree into the final site.

    Args:
        repo_root: Repository root that may contain an ``info/`` directory.
        output_dir: Site root where rendered and copied info files should be
            written.

    Returns:
        ``True`` when ``info/`` existed and was processed, otherwise ``False``.

    Raises:
        NotADirectoryError: If ``repo_root / "info"`` exists but is not a
            directory.
        ValueError: If two input files map to the same output path or if an
            input file conflicts with reserved site paths such as ``docs/``.
    """

    info_dir = repo_root / "info"
    if not info_dir.exists():
        return False

    if not info_dir.is_dir():
        raise NotADirectoryError(f"{info_dir} exists but is not a directory.")

    reserved_paths = {"docs"}
    seen_outputs: dict[Path, Path] = {}

    for source_path in iter_info_files(info_dir):
        relative_path = source_path.relative_to(info_dir)
        if relative_path.parts and relative_path.parts[0] in reserved_paths:
            # info/docs would collide with the versioned docs subtree created elsewhere.
            raise ValueError(
                f"info/{relative_path.as_posix()} conflicts with a reserved Pages path; "
                "place documentation-independent site files outside info/docs."
            )

        output_relative_path = info_output_relative_path(info_dir, source_path)
        previous_source = seen_outputs.get(output_relative_path)
        if previous_source is not None:
            # Two different inputs may not claim the same published path.
            raise ValueError(
                "Multiple info/ files map to the same output path: "
                f"{previous_source.relative_to(info_dir).as_posix()} and "
                f"{relative_path.as_posix()} -> {output_relative_path.as_posix()}"
            )
        seen_outputs[output_relative_path] = source_path

    for output_relative_path, source_path in seen_outputs.items():
        destination = output_dir / output_relative_path
        root_prefix = root_prefix_for_output(output_relative_path)
        current_path = output_relative_path.as_posix()
        suffix = source_path.suffix.lower()
        # Text-like inputs are normalized into wrapped HTML; other files are copied through.
        if suffix == ".rst":
            render_rst_info_page(source_path, destination, root_prefix, current_path)
        elif suffix == ".txt":
            render_plain_text_info_page(source_path, destination, root_prefix, current_path)
        elif suffix == ".html":
            inject_nav_into_html(source_path, destination, root_prefix, current_path)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            # Non-rendered assets such as images are copied byte-for-byte.
            shutil.copy2(source_path, destination)

    return True
