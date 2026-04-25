"""Git and hashing helpers used to materialize and deduplicate docs builds.

These helpers isolate direct Git process calls and the content hashing logic
used to decide whether multiple versions can reuse the same canonical build.
"""

import hashlib
import subprocess
import tarfile
from pathlib import Path

from thornforge.buildsite.constant import (
    ASSET_ROOT,
    INJECTED_CONF_MARKER,
    SHARED_CSS_ASSET_PATHS,
    TOP_NAV_SCRIPT_ASSET_PATH,
    VERSION_SWITCHER_SCRIPT_ASSET_PATH,
    VERSIONS_TEMPLATE_ASSET_PATH,
)


def run_git(repo_root: Path, *args: str) -> str:
    """Run a Git command that is expected to return text.

    Args:
        repo_root: Repository root used as the subprocess working directory.
        *args: Positional arguments passed after the ``git`` executable.

    Returns:
        Standard output from the Git subprocess with surrounding whitespace
        stripped.

    Raises:
        subprocess.CalledProcessError: If the Git command exits with a non-zero
            status.
    """

    # Capture stdout because callers typically need the command result immediately.
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def run_git_binary(repo_root: Path, *args: str) -> bytes:
    """Run a Git command that should return binary-safe output.

    Args:
        repo_root: Repository root used as the subprocess working directory.
        *args: Positional arguments passed after the ``git`` executable.

    Returns:
        Raw bytes from standard output. This is used for tree inspection and
        hashing workflows where text decoding would be lossy.
    """

    # Binary mode avoids accidental decoding changes for null-delimited Git output.
    completed = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        check=True,
        capture_output=True,
    )
    return completed.stdout


def is_git_repository(repo_root: Path) -> bool:
    """Return whether ``repo_root`` behaves like a usable Git repository.

    Args:
        repo_root: Candidate repository root to probe.

    Returns:
        ``True`` when ``git rev-parse --show-toplevel`` succeeds in that
        directory, otherwise ``False``.
    """

    try:
        # rev-parse is a cheap way to prove the directory is inside a valid repository.
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
    """Build a stable cache key for a tagged repository version.

    Args:
        repo_root: Git repository root from which tree objects are read.
        tag: Git reference naming the version to hash.
        input_paths: Repository-relative paths that should contribute to the
            build key, typically docs sources and metadata files.

    Returns:
        A short hexadecimal digest string used as the canonical build directory
        name for this version.

    Notes:
        The hash includes both repository content and ThornForge-owned assets so
        rebuilt output changes when the shared UI assets change.
    """

    digest = hashlib.sha256()
    # Ask Git for tree entries directly so the digest depends on committed objects, not checkout state.
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
        # Git object ids make the hash independent of checkout timestamps and permissions.
        object_id = metadata.rsplit(b" ", 1)[-1]
        # Mix both the file path and the object id into the digest to avoid rename collisions.
        digest.update(path_bytes)
        digest.update(b"\0")
        digest.update(object_id)
        digest.update(b"\0")

    # Shared ThornForge assets affect rendered output, so they must affect the cache key too.
    update_asset_digest(digest)

    # The injected config fragment changes output even though it is not stored in the target repo.
    digest.update(INJECTED_CONF_MARKER.encode("utf-8"))
    return digest.hexdigest()[:16]


def hash_worktree_inputs(repo_root: Path, input_paths: tuple[str, ...]) -> str:
    """Build a cache key for a non-tagged local working tree.

    Args:
        repo_root: Local repository directory whose on-disk files should be
            hashed.
        input_paths: Repository-relative paths that should participate in the
            digest.

    Returns:
        A short hexadecimal digest string used as the canonical build directory
        name for the current checkout.
    """

    digest = hashlib.sha256()

    for relative_path in input_paths:
        source_path = repo_root / relative_path
        if not source_path.exists():
            # Missing optional metadata files do not contribute to the digest.
            continue

        if source_path.is_file():
            # Hash standalone files directly using path plus content.
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(source_path.read_bytes())
            digest.update(b"\0")
            continue

        for path in sorted(source_path.rglob("*")):
            if not path.is_file():
                continue
            rel_path = path.relative_to(repo_root).as_posix()
            # Directory inputs are expanded into their leaf files for deterministic hashing.
            digest.update(rel_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(path.read_bytes())
            digest.update(b"\0")

    update_asset_digest(digest)
    digest.update(INJECTED_CONF_MARKER.encode("utf-8"))
    return digest.hexdigest()[:16]


def update_asset_digest(digest: "hashlib._Hash") -> None:
    """Mix ThornForge-owned asset files into an existing digest object.

    Args:
        digest: Mutable hash object that already contains repository-specific
            content.

    Side Effects:
        Reads shared CSS, JavaScript, and template asset files and appends their
        paths and contents into ``digest``.

    Returns:
        None. The supplied digest object is updated in place.
    """

    for relative_path in (
        *SHARED_CSS_ASSET_PATHS,
        TOP_NAV_SCRIPT_ASSET_PATH,
        VERSION_SWITCHER_SCRIPT_ASSET_PATH,
        VERSIONS_TEMPLATE_ASSET_PATH,
    ):
        source_path = ASSET_ROOT / relative_path
        # Include both path names and contents so renamed assets also invalidate cached builds.
        digest.update(relative_path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(source_path.read_bytes())
        digest.update(b"\0")


def extract_ref(repo_root: Path, ref: str, destination: Path) -> None:
    """Export a Git ref into a plain directory tree.

    Args:
        repo_root: Git repository root used as the source for ``git archive``.
        ref: Git reference to export, such as a tag or branch name.
        destination: Directory that should receive the extracted archive.

    Side Effects:
        Creates ``destination`` if needed and writes the archived repository
        contents into it without any Git metadata.

    Returns:
        None. Files are extracted to disk.
    """

    destination.mkdir(parents=True, exist_ok=True)
    # Stream the archive instead of checking out a worktree to keep the temp tree clean.
    archive = subprocess.Popen(
        ["git", "archive", "--format=tar", ref],
        cwd=repo_root,
        stdout=subprocess.PIPE,
    )
    assert archive.stdout is not None

    try:
        # tarfile handles directory creation while unpacking the archived repository snapshot.
        with tarfile.open(fileobj=archive.stdout, mode="r|") as tar:
            tar.extractall(destination, filter="data")
    finally:
        archive.stdout.close()

    return_code = archive.wait()
    if return_code != 0:
        raise subprocess.CalledProcessError(return_code, ["git", "archive", "--format=tar", ref])


def clone_repository(source_url: str, destination: Path) -> None:
    """Clone a remote repository to a local directory.

    Args:
        source_url: Remote Git URL to clone.
        destination: Local directory path that should receive the clone.

    Side Effects:
        Spawns ``git clone`` and writes repository contents to ``destination``.

    Returns:
        None.
    """

    # A quiet clone keeps CLI output readable while still failing loudly on errors.
    subprocess.run(
        ["git", "clone", "--quiet", source_url, str(destination)],
        check=True,
    )


def copy_worktree(source_root: Path, destination: Path) -> None:
    """Copy a local repository tree while excluding transient directories.

    Args:
        source_root: Existing local repository directory to copy from.
        destination: Destination directory that should receive the copied tree.

    Side Effects:
        Copies the repository contents to ``destination`` while skipping VCS and
        common cache directories that should not influence docs builds.

    Returns:
        None.
    """

    def ignore(_current_dir: str, names: list[str]) -> set[str]:
        """Return directory names that should be ignored by ``copytree``.

        Args:
            _current_dir: Current directory being visited by ``copytree``. The
                value is unused because the ignore set is static.
            names: Child entries present in the current directory.

        Returns:
            A subset of ``names`` that should not be copied.
        """

        ignored = {".git", ".hg", ".svn", "__pycache__", ".mypy_cache", ".pytest_cache"}
        return {name for name in names if name in ignored}

    # Local non-Git builds need a plain filesystem copy of the working tree.
    shutil_copytree(source_root, destination, ignore=ignore)


def shutil_copytree(source_root: Path, destination: Path, ignore) -> None:
    """Call ``shutil.copytree`` through a small local wrapper.

    Args:
        source_root: Source directory to copy.
        destination: Destination directory to create or merge into.
        ignore: Ignore callback forwarded to ``shutil.copytree``.

    Returns:
        None. Files are copied to disk.
    """

    import shutil

    shutil.copytree(source_root, destination, ignore=ignore, dirs_exist_ok=True)
