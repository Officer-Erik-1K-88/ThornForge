from __future__ import annotations

import html
from pathlib import Path
import shutil
from typing import Iterable

from thornforge.constant import INFO_RENDERED_SUFFIXES
from thornforge.nav import wrap_info_html_document


def iter_info_files(info_dir: Path) -> Iterable[Path]:
    for path in sorted(info_dir.rglob("*")):
        if path.is_file():
            yield path


def info_output_relative_path(info_dir: Path, source_path: Path) -> Path:
    relative_path = source_path.relative_to(info_dir)
    if source_path.suffix.lower() in INFO_RENDERED_SUFFIXES:
        return relative_path.with_suffix(".html")
    return relative_path


def root_prefix_for_output(output_relative_path: Path) -> str:
    parent = output_relative_path.parent
    if str(parent) == ".":
        return ""
    return "../" * len(parent.parts)


def render_rst_info_page(source_path: Path, destination: Path, root_prefix: str, current_path: str) -> None:
    from docutils.core import publish_parts

    source = source_path.read_text(encoding="utf-8")
    parts = publish_parts(source=source, writer_name="html5")
    title = parts.get("title", source_path.stem)
    body_html = parts.get("body") or parts.get("whole") or ""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        wrap_info_html_document(
            body_html,
            root_prefix,
            title=title,
            current_path=current_path,
        ),
        encoding="utf-8",
    )


def render_plain_text_info_page(source_path: Path, destination: Path, root_prefix: str, current_path: str) -> None:
    text = html.escape(source_path.read_text(encoding="utf-8"))
    title = source_path.stem
    body_html = f"<pre>{text}</pre>"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        wrap_info_html_document(
            body_html,
            root_prefix,
            title=title,
            current_path=current_path,
        ),
        encoding="utf-8",
    )


def inject_nav_into_html(source_path: Path, destination: Path, root_prefix: str, current_path: str) -> None:
    document = source_path.read_text(encoding="utf-8")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        wrap_info_html_document(
            document,
            root_prefix,
            title=source_path.stem,
            current_path=current_path,
        ),
        encoding="utf-8",
    )


def copy_info_site(repo_root: Path, output_dir: Path) -> bool:
    info_dir = repo_root / "info"
    if not info_dir.exists():
        return False

    if not info_dir.is_dir():
        raise NotADirectoryError(f"{info_dir} exists but is not a directory.")

    reserved_paths = {"docs"}
    seen_outputs: dict[Path, Path] = {}

    for source_path in iter_info_files(info_dir):
        relative_path = source_path.relative_to(info_dir)
        if relative_path.parts and relative_path.parts[0] in reserved_paths:
            raise ValueError(
                f"info/{relative_path.as_posix()} conflicts with a reserved Pages path; "
                "place documentation-independent site files outside info/docs."
            )

        output_relative_path = info_output_relative_path(info_dir, source_path)
        previous_source = seen_outputs.get(output_relative_path)
        if previous_source is not None:
            raise ValueError(
                "Multiple info/ files map to the same output path: "
                f"{previous_source.relative_to(info_dir).as_posix()} and "
                f"{relative_path.as_posix()} -> {output_relative_path.as_posix()}"
            )
        seen_outputs[output_relative_path] = source_path

    for output_relative_path, source_path in seen_outputs.items():
        destination = output_dir / output_relative_path
        root_prefix = root_prefix_for_output(output_relative_path)
        current_path = output_relative_path.as_posix()
        suffix = source_path.suffix.lower()
        if suffix == ".rst":
            render_rst_info_page(source_path, destination, root_prefix, current_path)
        elif suffix == ".txt":
            render_plain_text_info_page(source_path, destination, root_prefix, current_path)
        elif suffix == ".html":
            inject_nav_into_html(source_path, destination, root_prefix, current_path)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source_path, destination)

    return True
