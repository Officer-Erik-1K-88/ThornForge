import html
import re

from thornforge.constant import build_site_nav_script_src, build_stylesheet_hrefs


def build_site_nav_placeholder_html(
    root_prefix: str,
    *,
    current_path: str,
    current_label: str | None = None,
) -> str:
    label_attr = f' data-current-label="{html.escape(current_label, quote=True)}"' if current_label else ""
    return (
        '<nav class="site-top-nav" aria-label="Site"'
        f' data-site-root-prefix="{html.escape(root_prefix, quote=True)}"'
        f' data-current-path="{html.escape(current_path, quote=True)}"{label_attr}></nav>'
    )


def inject_document_assets(document: str, stylesheet_hrefs: list[str], script_srcs: list[str]) -> str:
    wrapped = document.strip()
    lowered = wrapped.lower()

    if "<head" not in lowered:
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
        script_block = "\n".join(missing_script_tags)
        if "</body>" in lowered:
            wrapped = re.sub(r"</body>", script_block + "\n</body>", wrapped, count=1, flags=re.IGNORECASE)
            lowered = wrapped.lower()
        else:
            wrapped += "\n" + script_block
            lowered = wrapped.lower()

    return wrapped


def wrap_info_html_document(document: str, root_prefix: str, *, title: str = "PieThorn", current_path: str) -> str:
    safe_title = html.escape(title)
    nav_html = build_site_nav_placeholder_html(root_prefix, current_path=current_path)
    wrapped = document.strip()
    lowered = wrapped.lower()

    has_html = "<html" in lowered
    has_head = "<head" in lowered
    has_body = "<body" in lowered

    if not has_html:
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

    wrapped = inject_document_assets(wrapped, build_stylesheet_hrefs(root_prefix), [build_site_nav_script_src(root_prefix)])
    lowered = wrapped.lower()
    has_nav = '<nav class="site-top-nav"' in lowered

    if "<title" not in lowered and "</head>" in lowered:
        wrapped = re.sub(r"</head>", f"<title>{safe_title}</title>\n</head>", wrapped, count=1, flags=re.IGNORECASE)
        lowered = wrapped.lower()

    if "<body" in lowered and not has_nav:
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
            wrapped = f"{nav_html}\n<main class=\"info-page__content\">\n{wrapped}\n</main>"

    return wrapped
