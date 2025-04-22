"""
Utility functions for the nutrition and exercise coach API.
"""
import re
from markupsafe import escape

def format_response_as_html(text: str) -> str:
    """
    Convert markdown-formatted text to HTML.
    Handles headings, lists, key-value pairs, and paragraphs.
    """
    lines = text.strip().splitlines()
    html = []
    in_ul = False
    in_ol = False

    for line in lines:
        stripped = line.strip()

        if stripped.startswith("**") and stripped.endswith("**"):
            stripped = stripped[2:-2].strip()

        if stripped.startswith("### "):
            html.append(f"<h3>{escape(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            html.append(f"<h2>{escape(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            html.append(f"<h1>{escape(stripped[2:])}</h1>")

        elif stripped.startswith("- "):
            if not in_ul:
                html.append("<ul>")
                in_ul = True
            html.append(f"<li>{escape(stripped[2:])}</li>")

        elif re.match(r"^\d+\.\s", stripped):
            if not in_ol:
                html.append("<ol>")
                in_ol = True
            item = re.sub(r"^\d+\.\s", "", stripped)
            html.append(f"<li>{escape(item)}</li>")

        elif ":" in stripped and not stripped.startswith("http"):
            key, value = stripped.split(":", 1)
            html.append(f"<p><strong>{escape(key.strip())}:</strong> {escape(value.strip())}</p>")

        elif not stripped:
            if in_ul:
                html.append("</ul>")
                in_ul = False
            if in_ol:
                html.append("</ol>")
                in_ol = False
            html.append("<br>")

        else:
            html.append(f"<p>{escape(stripped)}</p>")

    if in_ul:
        html.append("</ul>")
    if in_ol:
        html.append("</ol>")

    return "\n".join(html)