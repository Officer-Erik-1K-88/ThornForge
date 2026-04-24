import hashlib
import subprocess
import tarfile
from pathlib import Path

from thornforge.constant import (
    ASSET_ROOT,
    INJECTED_CONF_MARKER,
    SHARED_CSS_ASSET_PATHS,
    TOP_NAV_SCRIPT_ASSET_PATH,
    VERSION_SWITCHER_SCRIPT_ASSET_PATH,
    VERSIONS_TEMPLATE_ASSET_PATH,
)


def run_git(repo_root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def run_git_binary(repo_root: Path, *args: str) -> bytes:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def is_git_repository(repo_root: Path) -> bool:
    try:
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except subprocess.CalledProcessError:
        return False
    return True


def hash_version_inputs(repo_root: Path, tag: str, input_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    ls_tree_output = run_git_binary(
        repo_root,
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        tag,
        "--",
        *input_paths,
    )

    for entry in ls_tree_output.split(b"\0"):
        if not entry:
            continue
        metadata, path_bytes = entry.split(b"\t", 1)
        object_id = metadata.rsplit(b" ", 1)[-1]
        digest.update(path_bytes)
        digest.update(b"\0")
        digest.update(object_id)
        digest.update(b"\0")

    update_asset_digest(digest)

    digest.update(INJECTED_CONF_MARKER.encode("utf-8"))
    return digest.hexdigest()[:16]


def hash_worktree_inputs(repo_root: Path, input_paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()

    for relative_path in input_paths:
        source_path = repo_root / relative_path
        if not source_path.exists():
            continue

        if source_path.is_file():
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(source_path.read_bytes())
            digest.update(b"\0")
            continue

        for path in sorted(source_path.rglob("*")):
            if not path.is_file():
                continue
            rel_path = path.relative_to(repo_root).as_posix()
            digest.update(rel_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")

    update_asset_digest(digest)
    digest.update(INJECTED_CONF_MARKER.encode("utf-8"))
    return digest.hexdigest()[:16]


def update_asset_digest(digest: "hashlib._Hash") -> None:
    for relative_path in (
        *SHARED_CSS_ASSET_PATHS,
        TOP_NAV_SCRIPT_ASSET_PATH,
        VERSION_SWITCHER_SCRIPT_ASSET_PATH,
        VERSIONS_TEMPLATE_ASSET_PATH,
    ):
        source_path = ASSET_ROOT / relative_path
        digest.update(relative_path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(source_path.read_bytes())
        digest.update(b"\0")


def extract_ref(repo_root: Path, ref: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    archive = subprocess.Popen(
        ["git", "archive", "--format=tar", ref],
        cwd=repo_root,
        stdout=subprocess.PIPE,
    )
    assert archive.stdout is not None

    try:
        with tarfile.open(fileobj=archive.stdout, mode="r|") as tar:
            tar.extractall(destination, filter="data")
    finally:
        archive.stdout.close()

    return_code = archive.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, ["git", "archive", "--format=tar", ref])


def clone_repository(source_url: str, destination: Path) -> None:
    subprocess.run(
        ["git", "clone", "--quiet", source_url, str(destination)],
        check=True,
    )


def copy_worktree(source_root: Path, destination: Path) -> None:
    def ignore(_current_dir: str, names: list[str]) -> set[str]:
        ignored = {".git", ".hg", ".svn", "__pycache__", ".mypy_cache", ".pytest_cache"}
        return {name for name in names if name in ignored}

    shutil_copytree(source_root, destination, ignore=ignore)


def shutil_copytree(source_root: Path, destination: Path, ignore) -> None:
    import shutil

    shutil.copytree(source_root, destination, ignore=ignore, dirs_exist_ok=True)
