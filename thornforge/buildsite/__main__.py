import argparse
from pathlib import Path
from typing import Sequence

from thornforge.buildsite.build_site import build_versioned_site


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments for the build command.

    Returns:
        An ``argparse.Namespace`` containing:
        ``source``: local path or GitHub repository URL to build.
        ``output``: destination directory for the generated static site.
    """

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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    """Entry point used by ``python -m thornforge.build_versioned_docs``.

    The function parses command-line arguments, normalizes local paths to
    absolute paths, and then delegates the actual build to
    ``build_versioned_site``.
    """

    args = parse_args(argv)
    # Preserve remote URLs as strings but normalize existing local paths to absolute paths.
    source = Path(args.source).resolve() if Path(args.source).exists() else args.source
    build_versioned_site(source, args.output.resolve())


if __name__ == "__main__":
    main()
