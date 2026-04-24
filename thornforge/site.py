from __future__ import annotations

import html
import json
from pathlib import Path
import re

from thornforge.builder import make_relative_symlink
from thornforge.constant import build_site_nav_script_src, build_stylesheet_hrefs, load_html_template
from thornforge.info_site import root_prefix_for_output
from thornforge.nav import build_site_nav_placeholder_html, wrap_info_html_document


def render_project_site_pages(
    repo_root: Path,
    output_dir: Path,
    project_pages: tuple[tuple[Path, Path], ...],
) -> None:
    for source_relative_path, output_relative_path in project_pages:
        source_path = repo_root / source_relative_path
        if not source_path.exists():
            continue

        destination = output_dir / output_relative_path
        if destination.exists() or destination.is_symlink():
            raise ValueError(
                f"Project site page output conflict: {output_relative_path.as_posix()} "
                f"already exists before rendering {source_relative_path.as_posix()}."
            )

        root_prefix = root_prefix_for_output(output_relative_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            wrap_info_html_document(
                source_path.read_text(encoding="utf-8"),
                root_prefix,
                title=source_path.stem,
                current_path=output_relative_path.as_posix(),
            ),
            encoding="utf-8",
        )


def label_from_output_path(output_path: Path) -> str:
    if output_path == Path("index.html"):
        return "Home"

    if output_path.name == "index.html" and output_path.parent != Path("."):
        source = output_path.parent.name
    else:
        source = output_path.stem

    return source.replace("-", " ").replace("_", " ").title()


def extract_html_title(html_path: Path) -> str | None:
    content = html_path.read_text(encoding="utf-8")
    match = re.search(r"<title>(.*?)</title>", content, flags=re.IGNORECASE | re.DOTALL)
    if not match:
        return None
    return html.unescape(match.group(1)).strip() or None


def collect_site_nav_pages(output_dir: Path) -> list[dict[str, str]]:
    pages: list[dict[str, str]] = []

    for html_path in sorted(output_dir.rglob("*.html")):
        relative_path = html_path.relative_to(output_dir)
        if not relative_path.parts:
            continue
        if relative_path.parts[0] in {"docs", "assets"}:
            continue

        label = label_from_output_path(relative_path)
        if relative_path != Path("index.html"):
            label = extract_html_title(html_path) or label
        pages.append({"label": label, "path": relative_path.as_posix()})

    pages.sort(key=lambda page: (page["path"] != "index.html", page["path"].count("/"), page["path"]))
    return pages


def write_site_nav_manifest(output_dir: Path, latest: str) -> dict[str, object]:
    payload = {
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
    nav_html = build_site_nav_placeholder_html("", current_path="index.html")
    stylesheet_links = "\n    ".join(
        f'<link rel="stylesheet" href="{html.escape(href, quote=True)}">' for href in build_stylesheet_hrefs("")
    )
    script_src = build_site_nav_script_src("")
    index_html = load_html_template("homepage.html").format(
        project_name=html.escape(project_name),
        stylesheet_links=stylesheet_links,
        nav_html=nav_html,
        latest=html.escape(latest),
        script_src=html.escape(script_src, quote=True),
    )
    (output_dir / "index.html").write_text(index_html, encoding="utf-8")


def write_docs_site_files(docs_dir: Path, versions: list[str], digests: dict[str, str]) -> dict[str, object]:
    latest = versions[-1]
    payload = {
        "latest": latest,
        "versions": [{"name": version, "path": f"{version}/"} for version in reversed(versions)],
        "builds": {version: digests[version] for version in versions},
    }
    (docs_dir / "versions.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    index_html = load_html_template("docs-index.html").format(latest=html.escape(latest))
    (docs_dir / "index.html").write_text(index_html, encoding="utf-8")
    make_relative_symlink(docs_dir / versions[-1], docs_dir / "latest")
    return payload


def build_inline_json_script(script_id: str, payload: object) -> str:
    serialized = json.dumps(payload, indent=2).replace("</", "<\\/")
    return f'<script id="{script_id}" type="application/json">\n{serialized}\n</script>'


def inject_inline_json_scripts(document: str, scripts: list[str]) -> str:
    if not scripts:
        return document

    block = "\n".join(scripts)
    if re.search(r"</body>", document, flags=re.IGNORECASE):
        return re.sub(r"</body>", block + "\n</body>", document, count=1, flags=re.IGNORECASE)
    return document + "\n" + block


def embed_runtime_data(output_dir: Path, site_nav_payload: dict[str, object], versions_payload: dict[str, object]) -> None:
    site_nav_script = build_inline_json_script("site-nav-data", site_nav_payload)
    versions_script = build_inline_json_script("versions-data", versions_payload)

    for html_path in sorted(output_dir.rglob("*.html")):
        relative_path = html_path.relative_to(output_dir)
        if not relative_path.parts or relative_path.parts[0] == "assets":
            continue

        scripts = [site_nav_script]
        if relative_path.parts[0] == "docs" and relative_path.name.endswith(".html"):
            scripts.append(versions_script)

        content = html_path.read_text(encoding="utf-8")
        if 'id="site-nav-data"' in content:
            scripts = [script for script in scripts if 'id="site-nav-data"' not in script]
        if 'id="versions-data"' in content:
            scripts = [script for script in scripts if 'id="versions-data"' not in script]
        if not scripts:
            continue

        html_path.write_text(inject_inline_json_scripts(content, scripts), encoding="utf-8")
