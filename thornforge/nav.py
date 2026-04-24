"""HTML rewriting helpers for injecting ThornForge navigation and assets.

These functions normalize generated HTML enough that shared CSS, JavaScript,
navigation placeholders, and content wrappers can be inserted consistently even
when the source HTML is incomplete or fragmentary.
"""

import html
import re

from thornforge.constant import build_site_nav_script_src, build_stylesheet_hrefs


def build_site_nav_placeholder_html(
    root_prefix: str,
    *,
    current_path: str,
    current_label: str | None = None,
) -> str:
    """Build the placeholder element consumed by the runtime top-nav script.

    Args:
        root_prefix: Relative path from the current page back to the site root.
        current_path: Site-relative path of the current page.
        current_label: Optional precomputed label to display in the nav metadata.

    Returns:
        HTML string for a ``<nav>`` placeholder whose data attributes are later
        read by ``assets/scripts/top-nav.js``.
    """

    label_attr = f' data-current-label="{html.escape(current_label, quote=True)}"' if current_label else ""
    # The placeholder is intentionally empty; JS fills it once runtime metadata is available.
    return (
        '<nav class="site-top-nav" aria-label="Site"'
        f' data-site-root-prefix="{html.escape(root_prefix, quote=True)}"'
        f' data-current-path="{html.escape(current_path, quote=True)}"{label_attr}></nav>'
    )


def inject_document_assets(document: str, stylesheet_hrefs: list[str], script_srcs: list[str]) -> str:
    """Ensure an HTML document references the requested CSS and JS assets.

    Args:
        document: Existing HTML document or fragment to modify.
        stylesheet_hrefs: Asset-relative stylesheet URLs that must be linked
            from the document.
        script_srcs: Asset-relative script URLs that must be loaded by the
            document.

    Returns:
        Updated HTML text containing the requested stylesheet links and script
        tags exactly once, with missing ``head`` or ``body`` sections created as
        needed.
    """

    wrapped = document.strip()
    lowered = wrapped.lower()

    if "<head" not in lowered:
        # Fragments may omit a head entirely, so create the minimum valid structure needed for assets.
        wrapped = re.sub(
            r"(<html[^>]*>)",
            r"\1\n<head>\n<meta charset=\"utf-8\">\n<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n</head>",
            wrapped,
            count=1,
            flags=re.IGNORECASE,
        )
        lowered = wrapped.lower()

    if "<body" not in lowered:
        html_close_match = re.search(r"</html>", wrapped, flags=re.IGNORECASE)
        head_close_match = re.search(r"</head>", wrapped, flags=re.IGNORECASE)
        if html_close_match and head_close_match:
            # Preserve any loose content between head and html by moving it into body.
            body_inner = wrapped[head_close_match.end():html_close_match.start()].strip()
            wrapped = (
                wrapped[:head_close_match.end()]
                + "\n<body>\n"
                + body_inner
                + "\n</body>\n"
                + wrapped[html_close_match.start():]
            )
        elif head_close_match:
            wrapped = wrapped[:head_close_match.end()] + "\n<body>\n</body>" + wrapped[head_close_match.end():]
        else:
            wrapped += "\n<body>\n</body>"
        lowered = wrapped.lower()

    missing_stylesheet_links = [
        f'<link rel="stylesheet" href="{html.escape(stylesheet_href, quote=True)}">'
        for stylesheet_href in stylesheet_hrefs
        if stylesheet_href not in wrapped
    ]
    if missing_stylesheet_links:
        # Only add links that are not already present so repeated passes stay idempotent.
        stylesheet_block = "\n".join(missing_stylesheet_links)
        if "</head>" in lowered:
            wrapped = re.sub(r"</head>", stylesheet_block + "\n</head>", wrapped, count=1, flags=re.IGNORECASE)
            lowered = wrapped.lower()
        else:
            wrapped = stylesheet_block + "\n" + wrapped
            lowered = wrapped.lower()

    missing_script_tags = [
        f'<script src="{html.escape(script_src, quote=True)}" defer></script>'
        for script_src in script_srcs
        if script_src not in wrapped
    ]
    if missing_script_tags:
        # Scripts are also added idempotently so post-processing can be rerun safely.
        script_block = "\n".join(missing_script_tags)
        if "</body>" in lowered:
            wrapped = re.sub(r"</body>", script_block + "\n</body>", wrapped, count=1, flags=re.IGNORECASE)
            lowered = wrapped.lower()
        else:
            wrapped += "\n" + script_block
            lowered = wrapped.lower()

    return wrapped


def wrap_info_html_document(document: str, root_prefix: str, *, title: str = "PieThorn", current_path: str) -> str:
    """Wrap arbitrary HTML or fragments in ThornForge's shared page shell.

    Args:
        document: Existing HTML document or fragment to normalize.
        root_prefix: Relative prefix from the current page back to the site
            root, used for asset URLs.
        title: Title text to inject when the document does not already define
            one.
        current_path: Site-relative path for the page, used in the navigation
            placeholder.

    Returns:
        Fully wrapped HTML document text that includes shared assets, a top-nav
        placeholder, and a ``main.info-page__content`` container.
    """

    safe_title = html.escape(title)
    nav_html = build_site_nav_placeholder_html(root_prefix, current_path=current_path)
    wrapped = document.strip()
    lowered = wrapped.lower()

    has_html = "<html" in lowered
    has_head = "<head" in lowered
    has_body = "<body" in lowered

    if not has_html:
        # ``info/`` content may be a fragment, so synthesize the outer document structure.
        new_wrapped = f"<!DOCTYPE html>\n<html lang=\"en\">\n"
        if not has_head:
            new_wrapped += (
                "<head>\n"
                "<meta charset=\"utf-8\">\n"
                "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
                "</head>\n"
            )
        if has_head and has_body:
            new_wrapped += wrapped
        elif has_head:
            new_wrapped += f"{wrapped}\n<body>\n</body>"
        elif has_body:
            new_wrapped += wrapped
        else:
            new_wrapped += f"<body>\n{wrapped}\n</body>"
        new_wrapped += "\n</html>"
        wrapped = new_wrapped
        lowered = wrapped.lower()

    # Shared CSS and the top-nav runtime script are required for every wrapped info page.
    wrapped = inject_document_assets(wrapped, build_stylesheet_hrefs(root_prefix), [build_site_nav_script_src(root_prefix)])
    lowered = wrapped.lower()
    has_nav = '<nav class="site-top-nav"' in lowered

    if "<title" not in lowered and "</head>" in lowered:
        # Preserve existing titles, but fill one in when the source document omitted it.
        wrapped = re.sub(r"</head>", f"<title>{safe_title}</title>\n</head>", wrapped, count=1, flags=re.IGNORECASE)
        lowered = wrapped.lower()

    if "<body" in lowered and not has_nav:
        if re.search(r"<body[^>]*\bclass=", wrapped, flags=re.IGNORECASE):
            # Extend an existing class attribute instead of replacing it.
            wrapped = re.sub(
                r'(<body[^>]*\bclass=")([^"]*)(")',
                r'\1\2 info-page\3',
                wrapped,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            # Add the info-page marker when the body had no classes at all.
            wrapped = re.sub(r"(<body)([^>]*>)", r'\1 class="info-page"\2', wrapped, count=1, flags=re.IGNORECASE)
        # Put the navigation placeholder at the top of the body so JS can replace it later.
        wrapped = re.sub(r"(<body[^>]*>)", r"\1\n" + nav_html, wrapped, count=1, flags=re.IGNORECASE)
    elif "<body" not in lowered and not has_nav:
        wrapped = nav_html + wrapped

    if "<body" in wrapped.lower() and "info-page" not in wrapped.lower():
        if re.search(r"<body[^>]*\bclass=", wrapped, flags=re.IGNORECASE):
            wrapped = re.sub(
                r'(<body[^>]*\bclass=")([^"]*)(")',
                r'\1\2 info-page\3',
                wrapped,
                count=1,
                flags=re.IGNORECASE,
            )
        else:
            wrapped = re.sub(r"(<body)([^>]*>)", r'\1 class="info-page"\2', wrapped, count=1, flags=re.IGNORECASE)

    if "<main class=\"info-page__content\">" not in wrapped.lower():
        if "<body" in wrapped.lower():
            body_match = re.search(r"<body[^>]*>", wrapped, flags=re.IGNORECASE)
            if body_match:
                body_start = body_match.end()
                body_end_match = re.search(r"</body>", wrapped, flags=re.IGNORECASE)
                body_end = body_end_match.start() if body_end_match else len(wrapped)
                body_content = wrapped[body_start:body_end]
                if nav_html in body_content:
                    # Keep the nav outside the main content container for layout styling.
                    remaining = body_content.replace(nav_html, "", 1).strip()
                    wrapped = (
                        wrapped[:body_start]
                        + "\n"
                        + nav_html
                        + "\n<main class=\"info-page__content\">\n"
                        + remaining
                        + "\n</main>\n"
                        + wrapped[body_end:]
                    )
        else:
            # Fragments without a body get the same main wrapper synthesized directly.
            wrapped = f"{nav_html}\n<main class=\"info-page__content\">\n{wrapped}\n</main>"

    return wrapped
