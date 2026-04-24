from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

from thornforge.constant import (
    ASSET_ROOT,
    HTML_TEMPLATE_ROOT,
    INJECTED_CONF_MARKER,
)
from thornforge.info_site import root_prefix_for_output
from thornforge.nav import inject_document_assets
from thornforge.constant import build_site_nav_script_src, build_stylesheet_hrefs, build_version_switcher_script_src


def build_docs(worktree: Path, docs_source_dir: Path, output_dir: Path) -> None:
    if output_dir.exists():
        shutil.rmtree(output_dir)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(worktree) + os.pathsep + env.get("PYTHONPATH", "")

    subprocess.run(
        [
            sys.executable,
            "-m",
            "sphinx",
            "-b",
            "html",
            str(docs_source_dir),
            str(output_dir),
        ],
        check=True,
        env=env,
    )


def inject_shared_navigation(docs_root: Path) -> None:
    if not docs_root.exists():
        raise FileNotFoundError(f"Documentation root does not exist: {docs_root}")

    conf_path = docs_root / "conf.py"
    conf_text = conf_path.read_text(encoding="utf-8")
    if INJECTED_CONF_MARKER in conf_text:
        return

    conf_text += f"""

{INJECTED_CONF_MARKER}
templates_path = list(globals().get("templates_path", []))
_thornforge_templates_path = {str(HTML_TEMPLATE_ROOT)!r}
if _thornforge_templates_path not in templates_path:
    templates_path.append(_thornforge_templates_path)

_default_sidebars = ["about.html", "navigation.html", "relations.html", "searchbox.html", "versions.html"]
_existing_sidebars = dict(globals().get("html_sidebars", {{}}))
if not _existing_sidebars:
    _existing_sidebars["**"] = _default_sidebars
else:
    for _pattern, _templates in list(_existing_sidebars.items()):
        _merged = list(_templates)
        if "versions.html" not in _merged:
            _merged.append("versions.html")
        _existing_sidebars[_pattern] = _merged

html_sidebars = _existing_sidebars
"""
    conf_path.write_text(conf_text, encoding="utf-8")


def copy_shared_site_assets(output_dir: Path) -> None:
    destination_root = output_dir / "assets"
    if destination_root.exists():
        shutil.rmtree(destination_root)
    shutil.copytree(ASSET_ROOT, destination_root)


def inject_built_docs_assets(docs_output_dir: Path) -> None:
    copy_shared_site_assets(docs_output_dir)

    for html_path in sorted(docs_output_dir.rglob("*.html")):
        relative_path = html_path.relative_to(docs_output_dir)
        root_prefix = root_prefix_for_output(relative_path)
        content = html_path.read_text(encoding="utf-8")
        content = inject_document_assets(
            content,
            build_stylesheet_hrefs(root_prefix),
            [
                build_site_nav_script_src(root_prefix),
                build_version_switcher_script_src(root_prefix),
            ],
        )
        html_path.write_text(content, encoding="utf-8")


def make_relative_symlink(target: Path, link_path: Path) -> None:
    if link_path.exists() or link_path.is_symlink():
        if link_path.is_dir() and not link_path.is_symlink():
            shutil.rmtree(link_path)
        else:
            link_path.unlink()

    relative_target = os.path.relpath(target, link_path.parent)
    link_path.symlink_to(relative_target, target_is_directory=True)
