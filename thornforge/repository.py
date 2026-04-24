from __future__ import annotations
"""Repository discovery helpers for arbitrary local packages and GitHub repos.

This module converts a loose repository input into a concrete build profile:
where the docs live, which metadata files matter, which extra pages should be
published, and what version label should be displayed when no release tags are
available.
"""

from contextlib import contextmanager
from dataclasses import dataclass
import json
from pathlib import Path
import tempfile
import tomllib
from urllib.parse import urlparse

from thornforge.constant import METADATA_CANDIDATES, PROJECT_PAGE_CANDIDATES
from thornforge.git import clone_repository, is_git_repository, run_git


@dataclass(frozen=True)
class RepositoryProfile:
    """Resolved repository metadata needed to drive a ThornForge build.

    Attributes:
        repo_root: Absolute repository root used for all subsequent file lookups.
        docs_dir: Directory containing the Sphinx ``conf.py`` and source docs.
        project_name: Best-effort display name used in generated pages.
        input_paths: Repository-relative paths that should participate in build
            hashing so equivalent inputs can share the same output.
        project_pages: Mapping of source files to root-level published HTML
            outputs.
        default_version_name: Version label used when the repository does not
            provide matching release tags.
        is_git_repo: Whether ``repo_root`` is backed by a readable Git checkout.
    """

    repo_root: Path
    docs_dir: Path
    project_name: str
    input_paths: tuple[str, ...]
    project_pages: tuple[tuple[Path, Path], ...]
    default_version_name: str
    is_git_repo: bool


def discover_repository_profile(repo_root: Path) -> RepositoryProfile:
    """Discover the build-relevant structure of a target repository.

    Args:
        repo_root: Repository root to inspect.

    Returns:
        A ``RepositoryProfile`` containing resolved docs paths, metadata files,
        output page mappings, version defaults, and Git capability flags.
    """

    # Discover each piece independently so the heuristics stay simple and testable.
    docs_dir = discover_docs_dir(repo_root)
    project_pages = discover_project_site_pages(repo_root)
    input_paths = discover_input_paths(repo_root, docs_dir, project_pages)
    git_repo = is_git_repository(repo_root)
    return RepositoryProfile(
        repo_root=repo_root,
        docs_dir=docs_dir,
        project_name=discover_project_name(repo_root),
        input_paths=input_paths,
        project_pages=project_pages,
        default_version_name=discover_default_version_name(repo_root, git_repo),
        is_git_repo=git_repo,
    )


def discover_docs_dir(repo_root: Path) -> Path:
    """Find the most likely Sphinx documentation source directory.

    Args:
        repo_root: Repository root to inspect.

    Returns:
        The directory that most likely contains the project's Sphinx sources.
        Common layouts such as ``docs/`` and ``docs/source/`` are preferred
        before falling back to a broader ``conf.py`` search.

    Raises:
        FileNotFoundError: If no plausible Sphinx source directory can be found.
    """

    priority_candidates = (
        repo_root / "docs",
        repo_root / "docs" / "source",
        repo_root / "doc",
        repo_root / "doc" / "source",
        repo_root / "documentation",
        repo_root / "documentation" / "source",
    )

    for candidate in priority_candidates:
        # Favor conventional layouts before doing a slower recursive search.
        if (candidate / "conf.py").exists():
            return candidate

    excluded = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "_build", "build", "dist", "__pycache__"}
    matches: list[Path] = []
    for conf_path in repo_root.rglob("conf.py"):
        # Skip transient directories so cached outputs do not look like source docs.
        if any(part in excluded for part in conf_path.relative_to(repo_root).parts):
            continue
        matches.append(conf_path.parent)

    if not matches:
        raise FileNotFoundError(f"Could not find a Sphinx docs directory under {repo_root}")

    # Prefer shallower conf.py locations because they are more likely to be the primary docs root.
    matches.sort(key=lambda path: (len(path.relative_to(repo_root).parts), path.as_posix()))
    return matches[0]


def discover_project_name(repo_root: Path) -> str:
    """Infer a display name for the target project.

    Args:
        repo_root: Repository root whose metadata files should be inspected.

    Returns:
        Project name from ``pyproject.toml`` or ``package.json`` when available;
        otherwise the repository directory name.
    """

    pyproject_path = repo_root / "pyproject.toml"
    if pyproject_path.exists():
        # Python projects usually expose their canonical display name here.
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = data.get("project")
        if isinstance(project, dict) and isinstance(project.get("name"), str):
            return project["name"]

        poetry = data.get("tool", {}).get("poetry")
        if isinstance(poetry, dict) and isinstance(poetry.get("name"), str):
            return poetry["name"]

    package_json_path = repo_root / "package.json"
    if package_json_path.exists():
        # JavaScript repositories may only describe themselves through package.json.
        data = json.loads(package_json_path.read_text(encoding="utf-8"))
        if isinstance(data.get("name"), str):
            return data["name"]

    # Final fallback: use the repository directory name as a human-readable label.
    return repo_root.name


def discover_project_site_pages(repo_root: Path) -> tuple[tuple[Path, Path], ...]:
    """Map known metadata files to generated site pages.

    Args:
        repo_root: Repository root whose top-level files should be inspected.

    Returns:
        A tuple of ``(source_path, output_path)`` pairs describing which
        metadata files, such as README or CHANGELOG files, should be published
        as root-level HTML pages.
    """

    pages: list[tuple[Path, Path]] = []
    seen_outputs: set[Path] = set()

    for source_name, output_name in PROJECT_PAGE_CANDIDATES:
        source_path = repo_root / source_name
        output_path = Path(output_name)
        # First matching source for a given output path wins, so README.rst beats README.txt, etc.
        if not source_path.exists() or output_path in seen_outputs:
            continue
        pages.append((Path(source_name), output_path))
        seen_outputs.add(output_path)

    return tuple(pages)


def discover_input_paths(
    repo_root: Path,
    docs_dir: Path,
    project_pages: tuple[tuple[Path, Path], ...],
) -> tuple[str, ...]:
    """Build the repository-relative paths that should participate in hashing.

    Args:
        repo_root: Repository root used to test whether candidate files exist.
        docs_dir: Resolved documentation source directory.
        project_pages: Published project page mappings whose source files should
            also influence the build hash.

    Returns:
        Sorted repository-relative paths whose contents should influence the
        canonical build digest.
    """

    # The docs tree always matters because it directly drives the Sphinx output.
    paths = {docs_dir.relative_to(repo_root).as_posix()}
    for candidate in METADATA_CANDIDATES:
        if (repo_root / candidate).exists():
            # Existing metadata files can influence generated site pages or version labels.
            paths.add(candidate)
    for source_relative_path, _output_relative_path in project_pages:
        # Rendered project page sources also need to invalidate cached builds when they change.
        paths.add(source_relative_path.as_posix())
    return tuple(sorted(paths))


def discover_default_version_name(repo_root: Path, git_repo: bool) -> str:
    """Choose a fallback version label for repositories without release tags.

    Args:
        repo_root: Repository root used to inspect metadata or Git state.
        git_repo: Whether ``repo_root`` supports Git commands.

    Returns:
        A version string from ``pyproject.toml`` when present, otherwise a
        ``git describe`` result for Git repositories, otherwise ``"current"``.
    """

    pyproject_path = repo_root / "pyproject.toml"
    if pyproject_path.exists():
        # Static project metadata is the most explicit fallback version source.
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = data.get("project")
        if isinstance(project, dict) and isinstance(project.get("version"), str):
            return project["version"]

    if git_repo:
        try:
            # describe gives a more useful fallback than a raw commit hash when tags exist nearby.
            describe = run_git(repo_root, "describe", "--tags", "--always")
        except Exception:
            return "current"
        return describe or "current"

    return "current"


def is_remote_source(source: str) -> bool:
    """Return whether an input string looks like a supported GitHub remote.

    Args:
        source: Raw source string supplied by the user or CLI.

    Returns:
        ``True`` when the input resembles an HTTPS, SSH, or ``git@`` GitHub
        repository URL that ThornForge knows how to clone.
    """

    if source.startswith("git@github.com:"):
        return True

    # URL parsing handles HTTPS, SSH, and git:// forms consistently.
    parsed = urlparse(source)
    return parsed.scheme in {"http", "https", "ssh", "git"} and parsed.netloc.endswith("github.com")


@contextmanager
def materialize_source(source: str | Path):
    """Yield a local repository path for either a local or remote source.

    Args:
        source: Local path or GitHub URL describing the repository to build.

    Yields:
        A resolved local ``Path`` pointing at a repository tree that can be
        inspected and built.

    Side Effects:
        May create and later delete a temporary directory when ``source`` refers
        to a remote GitHub repository.

    Raises:
        FileNotFoundError: If ``source`` is neither an existing local path nor a
            supported GitHub remote URL.
    """

    if isinstance(source, Path):
        # Path inputs coming from callers can be resolved immediately and yielded directly.
        yield source.resolve()
        return

    source_text = str(source)
    candidate_path = Path(source_text)
    if candidate_path.exists():
        # String inputs that happen to be local paths are also treated as local repositories.
        yield candidate_path.resolve()
        return

    if not is_remote_source(source_text):
        raise FileNotFoundError(f"Source path does not exist: {source_text}")

    with tempfile.TemporaryDirectory(prefix="thornforge-source-") as temp_dir:
        destination = Path(temp_dir) / "repo"
        # Remote sources are cloned into a disposable directory that vanishes after the build.
        clone_repository(source_text, destination)
        yield destination.resolve()
