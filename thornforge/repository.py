from __future__ import annotations

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
    repo_root: Path
    docs_dir: Path
    project_name: str
    input_paths: tuple[str, ...]
    project_pages: tuple[tuple[Path, Path], ...]
    default_version_name: str
    is_git_repo: bool


def discover_repository_profile(repo_root: Path) -> RepositoryProfile:
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
    priority_candidates = (
        repo_root / "docs",
        repo_root / "docs" / "source",
        repo_root / "doc",
        repo_root / "doc" / "source",
        repo_root / "documentation",
        repo_root / "documentation" / "source",
    )

    for candidate in priority_candidates:
        if (candidate / "conf.py").exists():
            return candidate

    excluded = {".git", ".hg", ".svn", ".venv", "venv", "node_modules", "_build", "build", "dist", "__pycache__"}
    matches: list[Path] = []
    for conf_path in repo_root.rglob("conf.py"):
        if any(part in excluded for part in conf_path.relative_to(repo_root).parts):
            continue
        matches.append(conf_path.parent)

    if not matches:
        raise FileNotFoundError(f"Could not find a Sphinx docs directory under {repo_root}")

    matches.sort(key=lambda path: (len(path.relative_to(repo_root).parts), path.as_posix()))
    return matches[0]


def discover_project_name(repo_root: Path) -> str:
    pyproject_path = repo_root / "pyproject.toml"
    if pyproject_path.exists():
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = data.get("project")
        if isinstance(project, dict) and isinstance(project.get("name"), str):
            return project["name"]

        poetry = data.get("tool", {}).get("poetry")
        if isinstance(poetry, dict) and isinstance(poetry.get("name"), str):
            return poetry["name"]

    package_json_path = repo_root / "package.json"
    if package_json_path.exists():
        data = json.loads(package_json_path.read_text(encoding="utf-8"))
        if isinstance(data.get("name"), str):
            return data["name"]

    return repo_root.name


def discover_project_site_pages(repo_root: Path) -> tuple[tuple[Path, Path], ...]:
    pages: list[tuple[Path, Path]] = []
    seen_outputs: set[Path] = set()

    for source_name, output_name in PROJECT_PAGE_CANDIDATES:
        source_path = repo_root / source_name
        output_path = Path(output_name)
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
    paths = {docs_dir.relative_to(repo_root).as_posix()}
    for candidate in METADATA_CANDIDATES:
        if (repo_root / candidate).exists():
            paths.add(candidate)
    for source_relative_path, _output_relative_path in project_pages:
        paths.add(source_relative_path.as_posix())
    return tuple(sorted(paths))


def discover_default_version_name(repo_root: Path, git_repo: bool) -> str:
    pyproject_path = repo_root / "pyproject.toml"
    if pyproject_path.exists():
        data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
        project = data.get("project")
        if isinstance(project, dict) and isinstance(project.get("version"), str):
            return project["version"]

    if git_repo:
        try:
            describe = run_git(repo_root, "describe", "--tags", "--always")
        except Exception:
            return "current"
        return describe or "current"

    return "current"


def is_remote_source(source: str) -> bool:
    if source.startswith("git@github.com:"):
        return True

    parsed = urlparse(source)
    return parsed.scheme in {"http", "https", "ssh", "git"} and parsed.netloc.endswith("github.com")


@contextmanager
def materialize_source(source: str | Path):
    if isinstance(source, Path):
        yield source.resolve()
        return

    source_text = str(source)
    candidate_path = Path(source_text)
    if candidate_path.exists():
        yield candidate_path.resolve()
        return

    if not is_remote_source(source_text):
        raise FileNotFoundError(f"Source path does not exist: {source_text}")

    with tempfile.TemporaryDirectory(prefix="thornforge-source-") as temp_dir:
        destination = Path(temp_dir) / "repo"
        clone_repository(source_text, destination)
        yield destination.resolve()
