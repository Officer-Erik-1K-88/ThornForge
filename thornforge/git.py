import hashlib
import subprocess
import tarfile
from pathlib import Path

from thornforge.constant import SHARED_NAV_RELATIVE_PATHS, INJECTED_CONF_MARKER, DOC_INPUT_PATHS


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


def hash_version_inputs(repo_root: Path, tag: str) -> str:
    digest = hashlib.sha256()
    ls_tree_output = run_git_binary(
        repo_root,
        "ls-tree",
        "-r",
        "-z",
        "--full-tree",
        tag,
        "--",
        *DOC_INPUT_PATHS,
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

    # These files are injected into historical checkouts before the build.
    for relative_path in SHARED_NAV_RELATIVE_PATHS:
        source_path = repo_root / relative_path
        digest.update(relative_path.as_posix().encode("utf-8"))
        digest.update(b"\0")
        digest.update(source_path.read_bytes())
        digest.update(b"\0")

    digest.update(INJECTED_CONF_MARKER.encode("utf-8"))
    return digest.hexdigest()[:16]

def extract_tag(repo_root: Path, tag: str, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    archive = subprocess.Popen(
        ["git", "archive", "--format=tar", tag],
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
        raise subprocess.CalledProcessError(return_code, ["git", "archive", "--format=tar", tag])