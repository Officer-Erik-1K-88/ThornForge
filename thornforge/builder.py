from __future__ import annotations
"""Low-level helpers for invoking Sphinx and post-processing build outputs.

The functions in this module are intentionally small and filesystem-oriented.
They are responsible for running Sphinx, copying ThornForge-owned assets into
output trees, patching target ``conf.py`` files, and adjusting generated HTML
after Sphinx finishes.
"""

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
    """Run a single Sphinx HTML build.

    Args:
        worktree: Root directory of the extracted repository snapshot. This path
            is added to ``PYTHONPATH`` so project-local imports in ``conf.py``
            continue to work during the Sphinx build.
        docs_source_dir: Directory that contains the project's Sphinx sources,
            including ``conf.py`` and the documentation documents.
        output_dir: Destination directory for generated HTML. Any existing
            directory at this path is removed before Sphinx is invoked.

    Side Effects:
        Deletes and recreates ``output_dir``.
        Spawns a ``python -m sphinx -b html`` subprocess.

    Returns:
        None. The generated documentation is written to ``output_dir``.
    """

    if output_dir.exists():
        shutil.rmtree(output_dir)

    # Make the extracted repository importable for Sphinx conf.py and extensions.
    env = os.environ.copy()
    env["PYTHONPATH"] = str(worktree) + os.pathsep + env.get("PYTHONPATH", "")

    # Build plain HTML so ThornForge can post-process the generated pages afterward.
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
    """Patch a target ``conf.py`` to enable ThornForge's shared docs navigation.

    Args:
        docs_root: Sphinx source directory containing the target project's
            ``conf.py`` file.

    Side Effects:
        Appends a guarded configuration block to ``conf.py`` so the build uses
        ThornForge's shared ``versions.html`` template and ensures the sidebar
        configuration includes the version switcher.

    Returns:
        None. The function mutates ``docs_root / "conf.py"`` in place unless the
        injected marker already exists.

    Raises:
        FileNotFoundError: If ``docs_root`` does not exist.
    """

    if not docs_root.exists():
        raise FileNotFoundError(f"Documentation root does not exist: {docs_root}")

    conf_path = docs_root / "conf.py"
    conf_text = conf_path.read_text(encoding="utf-8")
    if INJECTED_CONF_MARKER in conf_text:
        # Avoid appending the same config block repeatedly on rebuilt worktrees.
        return

    # Append a self-contained config fragment instead of trying to parse Python AST.
    conf_text += f"""

{INJECTED_CONF_MARKER}
templates_path = list(globals().get("templates_path", []))
_thornforge_templates_path = {str(HTML_TEMPLATE_ROOT)!r}
# Keep the shared versions sidebar template outside the target repository.
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
    """Copy ThornForge-owned assets into a site tree.

    Args:
        output_dir: Directory that should receive an ``assets/`` subtree.

    Side Effects:
        Removes any pre-existing ``output_dir / "assets"`` directory and copies
        ThornForge's bundled asset tree into its place.

    Returns:
        None. Assets are copied onto disk.
    """

    destination_root = output_dir / "assets"
    if destination_root.exists():
        # Replace the full asset tree so removed files do not linger between builds.
        shutil.rmtree(destination_root)
    shutil.copytree(ASSET_ROOT, destination_root)


def inject_built_docs_assets(docs_output_dir: Path) -> None:
    """Post-process generated docs HTML so ThornForge assets are referenced.

    Args:
        docs_output_dir: Root directory containing generated documentation HTML
            for a single built version.

    Side Effects:
        Copies ThornForge's shared assets into ``docs_output_dir / "assets"``
        and rewrites each HTML file in place so it links to the shared
        stylesheets and JavaScript files.

    Returns:
        None. Updated HTML is written back to disk.
    """

    copy_shared_site_assets(docs_output_dir)

    for html_path in sorted(docs_output_dir.rglob("*.html")):
        relative_path = html_path.relative_to(docs_output_dir)
        # Each docs page needs asset URLs relative to its own nesting depth.
        root_prefix = root_prefix_for_output(relative_path)
        content = html_path.read_text(encoding="utf-8")
        # Inject both the global nav script and the version-switcher script into docs pages.
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
    """Create or replace a directory symlink using a relative target path.

    Args:
        target: Existing directory that the symlink should point to.
        link_path: Filesystem location where the symlink should be created.

    Side Effects:
        Deletes any pre-existing file, symlink, or directory at ``link_path``
        and replaces it with a relative symlink to ``target``.

    Returns:
        None. The symlink is created on disk.
    """

    if link_path.exists() or link_path.is_symlink():
        if link_path.is_dir() and not link_path.is_symlink():
            # Directories must be removed recursively before the symlink can replace them.
            shutil.rmtree(link_path)
        else:
            link_path.unlink()

    # Relative symlinks survive when the whole output directory is moved elsewhere.
    relative_target = os.path.relpath(target, link_path.parent)
    link_path.symlink_to(relative_target, target_is_directory=True)
