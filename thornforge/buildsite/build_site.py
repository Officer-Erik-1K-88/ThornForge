from __future__ import annotations
"""CLI entrypoint for assembling a versioned static documentation site.

This module coordinates the end-to-end build workflow:
1. Resolve a local repository path or clone a remote GitHub repository.
2. Discover where the target project's Sphinx sources and metadata live.
3. Build one or more documentation versions.
4. Assemble the final static site tree with shared assets and runtime metadata.
"""

from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile

from packaging.version import InvalidVersion, Version

from thornforge.buildsite.builder import (
    build_docs,
    copy_shared_site_assets,
    inject_built_docs_assets,
    inject_shared_navigation,
    make_relative_symlink,
)
from thornforge.buildsite.git import copy_worktree, extract_ref, hash_version_inputs, hash_worktree_inputs, run_git
from thornforge.buildsite.info_site import copy_info_site
from thornforge.buildsite.repository import discover_repository_profile, materialize_source
from thornforge.buildsite.site import (
    embed_runtime_data,
    render_project_site_pages,
    write_docs_site_files,
    write_homepage,
    write_site_nav_manifest,
)


@dataclass(frozen=True)
class BuildVersion:
    """Describe one logical documentation build target.

    Attributes:
        name: Human-readable version label written into the output tree, such as
            ``v1.2.0`` or ``current``.
        ref: Git reference used to materialize the source tree for this build.
            This is ``None`` when ThornForge should build directly from the
            current working tree instead of a tagged archive.
    """

    name: str
    ref: str | None


def collect_tags(repo_root: Path) -> list[str]:
    """Return documentation tags sorted in ascending version order.

    Args:
        repo_root: Repository root used as the working directory for ``git``.

    Returns:
        A list of tag names matching ``v*`` sorted with ``packaging.version`` so
        later release tags appear later in the list.

    Raises:
        SystemExit: If any matching tag cannot be parsed as a PEP 440 version
            after removing the leading ``v``.
    """

    # Ask Git for tags that look like versioned documentation releases.
    raw_tags = run_git(repo_root, "tag", "--list", "v*").splitlines()
    # Drop empty lines so later parsing only sees actual tag names.
    tags = [tag for tag in raw_tags if tag]
    try:
        # Sort with packaging.version semantics instead of plain string order.
        return sorted(tags, key=parse_version_tag)
    except InvalidVersion as error:
        raise SystemExit(f"Found non-PEP 440 documentation tag: {error}") from error


def parse_version_tag(tag: str) -> Version:
    """Parse a Git tag into a ``packaging.version.Version`` instance.

    Args:
        tag: Raw Git tag text, expected to use the common ``vX.Y.Z`` form.

    Returns:
        A parsed ``Version`` object used for deterministic sorting.
    """

    return Version(tag.removeprefix("v"))


def collect_build_versions(repo_root: Path, default_version_name: str, is_git_repo: bool) -> list[BuildVersion]:
    """Determine which logical versions ThornForge should build.

    Args:
        repo_root: Repository root used to inspect Git tags when available.
        default_version_name: Fallback version label for repositories that do
            not expose matching release tags.
        is_git_repo: Whether ``repo_root`` is a readable Git repository.

    Returns:
        A non-empty list of ``BuildVersion`` objects. Tagged repositories return
        one entry per ``v*`` tag. Non-Git repositories or repositories without
        matching tags return a single entry pointing at the current checkout.
    """

    if is_git_repo:
        # Prefer explicit release tags when the repository can answer Git queries.
        tags = collect_tags(repo_root)
        if tags:
            return [BuildVersion(name=tag, ref=tag) for tag in tags]
    # Repositories without matching tags still get one build from the current tree.
    return [BuildVersion(name=default_version_name, ref=None)]


def build_versioned_site(source: str | Path, output_dir: Path) -> None:
    """Build the final static site into ``output_dir``.

    Args:
        source: Either a local repository path or a GitHub URL. Local paths are
            used directly; remote URLs are cloned into a temporary directory
            before discovery and build steps begin.
        output_dir: Destination directory for the assembled site. The directory
            is deleted and recreated before the build so the result is fully
            deterministic.

    Side Effects:
        Removes any existing ``output_dir``.
        Writes built documentation, copied assets, JSON manifests, and symlinks
        under ``output_dir``.

    Returns:
        None. The result is the generated site tree on disk.
    """

    with materialize_source(source) as repo_root:
        # Resolve all repository-dependent paths and metadata before building.
        profile = discover_repository_profile(repo_root)
        versions = collect_build_versions(repo_root, profile.default_version_name, profile.is_git_repo)

        if output_dir.exists():
            # Start from a clean output tree so stale files cannot leak into the build.
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        # GitHub Pages should publish files that would otherwise be ignored by Jekyll.
        (output_dir / ".nojekyll").write_text("", encoding="utf-8")

        # The final site keeps docs under /docs and shared assets at the site root.
        docs_dir = output_dir / "docs"
        docs_dir.mkdir()
        copy_shared_site_assets(output_dir)

        # Canonical builds are stored by digest so identical inputs can be reused.
        build_root = docs_dir / "_builds"
        build_root.mkdir()

        digests_by_version: dict[str, str] = {}
        canonical_builds: dict[str, Path] = {}

        with tempfile.TemporaryDirectory(prefix="thornforge-docs-") as temp_dir:
            temp_root = Path(temp_dir)
            # Each version gets its own temporary extraction/copy location.
            worktree_root = temp_root / "worktrees"
            worktree_root.mkdir()

            for version in versions:
                safe_name = version.name.replace("/", "_")
                worktree_path = worktree_root / safe_name
                # Hashing lets identical inputs share one canonical build output.
                digest = (
                    hash_version_inputs(repo_root, version.ref, profile.input_paths)
                    if version.ref is not None
                    else hash_worktree_inputs(repo_root, profile.input_paths)
                )
                digests_by_version[version.name] = digest

                if digest not in canonical_builds:
                    if version.ref is not None:
                        # Tagged versions are materialized from Git archives.
                        extract_ref(repo_root, version.ref, worktree_path)
                    else:
                        # Untagged builds use the current local tree as-is.
                        copy_worktree(repo_root, worktree_path)

                    # Reconstruct the docs source path inside the extracted worktree.
                    docs_source_dir = worktree_path / profile.docs_dir.relative_to(repo_root)
                    # Patch the project's conf.py so ThornForge's shared navigation appears.
                    inject_shared_navigation(docs_source_dir)
                    canonical_path = build_root / digest
                    # Let Sphinx generate the HTML first.
                    build_docs(worktree_path, docs_source_dir, canonical_path)
                    # Sphinx owns its own assets; ThornForge adds site assets afterward.
                    inject_built_docs_assets(canonical_path)
                    canonical_builds[digest] = canonical_path

                # The public version path is just a symlink into the canonical build output.
                make_relative_symlink(canonical_builds[digest], docs_dir / version.name)

        latest = versions[-1].name
        # If the repository has no custom info/ homepage, synthesize a generic one.
        if not copy_info_site(repo_root, output_dir):
            write_homepage(output_dir, latest, profile.project_name)
        # README/changelog-style files are rendered after the homepage decision.
        render_project_site_pages(repo_root, output_dir, profile.project_pages)
        # The frontend scripts consume these manifests to build navigation UIs.
        site_nav_payload = write_site_nav_manifest(output_dir, latest)
        versions_payload = write_docs_site_files(docs_dir, [version.name for version in versions], digests_by_version)
        # Inline the manifests into HTML so pages still work without extra fetches.
        embed_runtime_data(output_dir, site_nav_payload, versions_payload)
