from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import shutil
import tempfile

from packaging.version import InvalidVersion, Version

from thornforge.builder import (
    build_docs,
    copy_shared_site_assets,
    inject_built_docs_assets,
    inject_shared_navigation,
    make_relative_symlink,
)
from thornforge.git import copy_worktree, extract_ref, hash_version_inputs, hash_worktree_inputs, run_git
from thornforge.info_site import copy_info_site
from thornforge.repository import discover_repository_profile, materialize_source
from thornforge.site import (
    embed_runtime_data,
    render_project_site_pages,
    write_docs_site_files,
    write_homepage,
    write_site_nav_manifest,
)


@dataclass(frozen=True)
class BuildVersion:
    name: str
    ref: str | None


def collect_tags(repo_root: Path) -> list[str]:
    raw_tags = run_git(repo_root, "tag", "--list", "v*").splitlines()
    tags = [tag for tag in raw_tags if tag]
    try:
        return sorted(tags, key=parse_version_tag)
    except InvalidVersion as error:
        raise SystemExit(f"Found non-PEP 440 documentation tag: {error}") from error


def parse_version_tag(tag: str) -> Version:
    return Version(tag.removeprefix("v"))


def collect_build_versions(repo_root: Path, default_version_name: str, is_git_repo: bool) -> list[BuildVersion]:
    if is_git_repo:
        tags = collect_tags(repo_root)
        if tags:
            return [BuildVersion(name=tag, ref=tag) for tag in tags]
    return [BuildVersion(name=default_version_name, ref=None)]


def build_versioned_site(source: str | Path, output_dir: Path) -> None:
    with materialize_source(source) as repo_root:
        profile = discover_repository_profile(repo_root)
        versions = collect_build_versions(repo_root, profile.default_version_name, profile.is_git_repo)

        if output_dir.exists():
            shutil.rmtree(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / ".nojekyll").write_text("", encoding="utf-8")

        docs_dir = output_dir / "docs"
        docs_dir.mkdir()
        copy_shared_site_assets(output_dir)

        build_root = docs_dir / "_builds"
        build_root.mkdir()

        digests_by_version: dict[str, str] = {}
        canonical_builds: dict[str, Path] = {}

        with tempfile.TemporaryDirectory(prefix="thornforge-docs-") as temp_dir:
            temp_root = Path(temp_dir)
            worktree_root = temp_root / "worktrees"
            worktree_root.mkdir()

            for version in versions:
                safe_name = version.name.replace("/", "_")
                worktree_path = worktree_root / safe_name
                digest = (
                    hash_version_inputs(repo_root, version.ref, profile.input_paths)
                    if version.ref is not None
                    else hash_worktree_inputs(repo_root, profile.input_paths)
                )
                digests_by_version[version.name] = digest

                if digest not in canonical_builds:
                    if version.ref is not None:
                        extract_ref(repo_root, version.ref, worktree_path)
                    else:
                        copy_worktree(repo_root, worktree_path)

                    docs_source_dir = worktree_path / profile.docs_dir.relative_to(repo_root)
                    inject_shared_navigation(docs_source_dir)
                    canonical_path = build_root / digest
                    build_docs(worktree_path, docs_source_dir, canonical_path)
                    inject_built_docs_assets(canonical_path)
                    canonical_builds[digest] = canonical_path

                make_relative_symlink(canonical_builds[digest], docs_dir / version.name)

        latest = versions[-1].name
        if not copy_info_site(repo_root, output_dir):
            write_homepage(output_dir, latest, profile.project_name)
        render_project_site_pages(repo_root, output_dir, profile.project_pages)
        site_nav_payload = write_site_nav_manifest(output_dir, latest)
        versions_payload = write_docs_site_files(docs_dir, [version.name for version in versions], digests_by_version)
        embed_runtime_data(output_dir, site_nav_payload, versions_payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build a documentation site from a local package or GitHub repository.")
    parser.add_argument(
        "--source",
        default=str(Path(__file__).resolve().parents[1]),
        help="Local package path or GitHub repository URL to build.",
    )
    parser.add_argument(
        "--repo-root",
        dest="source",
        help=argparse.SUPPRESS,
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Directory where the assembled static site should be written.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    source = Path(args.source).resolve() if Path(args.source).exists() else args.source
    build_versioned_site(source, args.output.resolve())


if __name__ == "__main__":
    main()
