from __future__ import annotations
"""Site-level HTML generation and runtime payload embedding.

This module handles the non-Sphinx parts of the generated site, including
root-level pages, docs redirect pages, navigation manifests, and inline JSON
payloads consumed by the frontend scripts.
"""

import html
import json
from pathlib import Path
import re

from thornforge.builder import make_relative_symlink
from thornforge.constant import build_site_nav_script_src, build_stylesheet_hrefs, load_html_template
from thornforge.info_site import root_prefix_for_output
from thornforge.nav import build_site_nav_placeholder_html, wrap_info_html_document


def render_project_page_body(source_path: Path) -> tuple[str, str]:
    """Convert one project metadata file into wrapped-page inputs.

    Args:
        source_path: Source metadata file such as ``README.rst`` or
            ``CHANGELOG.txt``.

    Returns:
        Tuple of ``(title, body_html)`` suitable for ``wrap_info_html_document``.
    """

    source = source_path.read_text(encoding="utf-8")
    suffix = source_path.suffix.lower()

    if suffix == ".rst":
        from docutils.core import publish_parts

        parts = publish_parts(source=source, writer_name="html5")
        title = parts.get("title", source_path.stem)
        body_html = parts.get("body") or parts.get("whole") or ""
        return title, body_html

    if suffix == ".txt":
        return source_path.stem, f"<pre>{html.escape(source)}</pre>"

    return source_path.stem, source


def render_project_site_pages(
    repo_root: Path,
    output_dir: Path,
    project_pages: tuple[tuple[Path, Path], ...],
) -> None:
    """Render metadata files such as README and CHANGELOG into site pages.

    Args:
        repo_root: Repository root containing the source metadata files.
        output_dir: Root directory of the generated site.
        project_pages: Sequence of ``(source_relative_path, output_relative_path)``
            pairs describing which files should be published and where.

    Side Effects:
        Writes wrapped HTML pages into ``output_dir``.

    Returns:
        None.
    """

    for source_relative_path, output_relative_path in project_pages:
        source_path = repo_root / source_relative_path
        if not source_path.exists():
            # Discovery should already filter missing files, but this keeps rendering defensive.
            continue

        destination = output_dir / output_relative_path
        if destination.exists() or destination.is_symlink():
            raise ValueError(
                f"Project site page output conflict: {output_relative_path.as_posix()} "
                f"already exists before rendering {source_relative_path.as_posix()}."
            )

        root_prefix = root_prefix_for_output(output_relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        title, body_html = render_project_page_body(source_path)
        # Reuse the info-page wrapper so metadata pages get the same shared navigation shell.
        destination.write_text(
            wrap_info_html_document(
                body_html,
                root_prefix,
                title=title,
                current_path=output_relative_path.as_posix(),
            ),
            encoding="utf-8",
        )


def label_from_output_path(output_path: Path) -> str:
    """Convert a generated output path into a human-friendly navigation label.

    Args:
        output_path: Path relative to the site root for a generated HTML page.

    Returns:
        Title-cased label text derived from the path, with special handling for
        ``index.html`` pages.
    """

    if output_path == Path("index.html"):
        return "Home"

    if output_path.name == "index.html" and output_path.parent != Path("."):
        # Nested index pages should use the directory name rather than the file stem.
        source = output_path.parent.name
    else:
        source = output_path.stem

    return source.replace("-", " ").replace("_", " ").title()


def extract_html_title(html_path: Path) -> str | None:
    """Extract the first ``<title>`` from an HTML file.

    Args:
        html_path: Path to an HTML file that has already been written to disk.

    Returns:
        Decoded title text if a title element is present and non-empty,
        otherwise ``None``.
    """

    content = html_path.read_text(encoding="utf-8")
    # A simple regex is enough here because we only need the first title tag from generated pages.
    match = re.search(r"<title>(.*?)</title>", content, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return html.unescape(match.group(1)).strip() or None


def collect_site_nav_pages(output_dir: Path) -> list[dict[str, str]]:
    """Collect root-level HTML pages for the runtime site navigation.

    Args:
        output_dir: Generated site root to scan.

    Returns:
        A sorted list of dictionaries containing ``label`` and ``path`` keys for
        non-docs HTML pages that should appear in the top navigation.
    """

    pages: list[dict[str, str]] = []

    for html_path in sorted(output_dir.rglob("*.html")):
        relative_path = html_path.relative_to(output_dir)
        if not relative_path.parts:
            continue
        if relative_path.parts[0] in {"docs", "assets"}:
            # Docs navigation is handled separately, and assets are never page entries.
            continue

        label = label_from_output_path(relative_path)
        if relative_path != Path("index.html"):
            label = extract_html_title(html_path) or label
        pages.append({"label": label, "path": relative_path.as_posix()})

    # Keep the homepage first, then shallower pages, then lexical order for stability.
    pages.sort(key=lambda page: (page["path"] != "index.html", page["path"].count("/"), page["path"]))
    return pages


def write_site_nav_manifest(output_dir: Path, latest: str) -> dict[str, object]:
    """Write the top-navigation manifest used by the frontend scripts.

    Args:
        output_dir: Generated site root where ``site-nav.json`` should be
            written.
        latest: Latest version label that should be exposed in nav metadata.

    Returns:
        The Python payload object that was serialized to ``site-nav.json``.
    """

    payload = {
        # Root pages and docs metadata are split because the frontend renders them differently.
        "pages": collect_site_nav_pages(output_dir),
        "docs": {
            "home": "docs/",
            "latest": "docs/latest/index.html",
            "latest_version": latest,
        },
    }
    (output_dir / "site-nav.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return payload


def write_homepage(output_dir: Path, latest: str, project_name: str) -> None:
    """Render the generated site homepage from a shared HTML template.

    Args:
        output_dir: Generated site root where ``index.html`` should be written.
        latest: Latest version label used to populate docs links.
        project_name: Display name inserted into the homepage title and hero.

    Side Effects:
        Writes ``output_dir / "index.html"``.

    Returns:
        None.
    """

    nav_html = build_site_nav_placeholder_html("", current_path="index.html")
    # Expand all stylesheet links eagerly because the HTML template expects rendered tags.
    stylesheet_links = "\n    ".join(
        f'<link rel="stylesheet" href="{html.escape(href, quote=True)}">' for href in build_stylesheet_hrefs("")
    )
    script_src = build_site_nav_script_src("")
    # The HTML template contains placeholders for the computed project and asset values.
    index_html = load_html_template("homepage.html").format(
        project_name=html.escape(project_name),
        stylesheet_links=stylesheet_links,
        nav_html=nav_html,
        latest=html.escape(latest),
        script_src=html.escape(script_src, quote=True),
    )
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")


def write_docs_site_files(docs_dir: Path, versions: list[str], digests: dict[str, str]) -> dict[str, object]:
    """Write docs-level helper files such as redirects and version metadata.

    Args:
        docs_dir: Root docs directory inside the generated site.
        versions: Ordered version labels that were built.
        digests: Mapping from version label to canonical build digest.

    Side Effects:
        Writes ``versions.json``, a redirecting docs ``index.html``, and the
        ``latest`` symlink inside ``docs_dir``.

    Returns:
        The Python payload object that was serialized to ``versions.json``.
    """

    latest = versions[-1]
    payload = {
        # Versions are reversed for the UI so the newest label appears first in menus.
        "latest": latest,
        "versions": [{"name": version, "path": f"{version}/"} for version in reversed(versions)],
        "builds": {version: digests[version] for version in versions},
    }
    (docs_dir / "versions.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    # The docs root redirects immediately to the moving "latest" alias.
    index_html = load_html_template("docs-index.html").format(latest=html.escape(latest))
    (docs_dir / "index.html").write_text(index_html, encoding="utf-8")
    make_relative_symlink(docs_dir / versions[-1], docs_dir / "latest")
    return payload


def build_inline_json_script(script_id: str, payload: object) -> str:
    """Serialize a Python object into an inline JSON ``<script>`` tag.

    Args:
        script_id: DOM id assigned to the generated script element.
        payload: JSON-serializable object to embed.

    Returns:
        HTML string containing a ``<script type="application/json">`` block.
    """

    # Escape </ so embedded JSON cannot accidentally terminate the surrounding script tag.
    serialized = json.dumps(payload, indent=2).replace("</", "<\\/")
    return f'<script id="{script_id}" type="application/json">\n{serialized}\n</script>'


def inject_inline_json_scripts(document: str, scripts: list[str]) -> str:
    """Insert inline JSON script blocks into an existing HTML document.

    Args:
        document: Existing HTML document text.
        scripts: Pre-rendered script tag strings to insert.

    Returns:
        Updated HTML with the script tags inserted before ``</body>`` when that
        closing tag exists, or appended to the end otherwise.
    """

    if not scripts:
        return document

    block = "\n".join(scripts)
    if re.search(r"</body>", document, flags=re.IGNORECASE):
        # Prefer insertion before </body> so the page remains valid and predictable.
        return re.sub(r"</body>", block + "\n</body>", document, count=1, flags=re.IGNORECASE)
    return document + "\n" + block


def embed_runtime_data(output_dir: Path, site_nav_payload: dict[str, object], versions_payload: dict[str, object]) -> None:
    """Embed JSON runtime payloads directly into generated HTML files.

    Args:
        output_dir: Site root whose HTML files should be post-processed.
        site_nav_payload: Navigation payload that every rendered page can use.
        versions_payload: Version payload used only by docs pages.

    Side Effects:
        Rewrites generated HTML files in place to add inline JSON payloads when
        those payloads are not already present.

    Returns:
        None.
    """

    site_nav_script = build_inline_json_script("site-nav-data", site_nav_payload)
    versions_script = build_inline_json_script("versions-data", versions_payload)

    for html_path in sorted(output_dir.rglob("*.html")):
        relative_path = html_path.relative_to(output_dir)
        if not relative_path.parts or relative_path.parts[0] == "assets":
            # Asset files are not HTML pages and should never be rewritten here.
            continue

        # Every page gets the top-nav data; docs pages also get version switcher data.
        scripts = [site_nav_script]
        if relative_path.parts[0] == "docs" and relative_path.name.endswith(".html"):
            scripts.append(versions_script)

        content = html_path.read_text(encoding="utf-8")
        if 'id="site-nav-data"' in content:
            # Skip payloads that were already embedded by a previous pass.
            scripts = [script for script in scripts if 'id="site-nav-data"' not in script]
        if 'id="versions-data"' in content:
            scripts = [script for script in scripts if 'id="versions-data"' not in script]
        if not scripts:
            continue

        # Write the updated page back in place once the final script list is known.
        html_path.write_text(inject_inline_json_scripts(content, scripts), encoding="utf-8")
