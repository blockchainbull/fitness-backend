"""
Utility functions for the nutrition and exercise coach API.
"""
import re
from markupsafe import escape
import html

def format_response_as_html(text: str) -> str:
    """
    Convert markdown-formatted text to HTML with proper entity handling.
    """
    # First, decode any HTML entities that might already be in the text
    text = html.unescape(text)
    
    lines = text.strip().splitlines()
    result_html = []
    in_ul = False
    in_ol = False

    for line in lines:
        stripped = line.strip()

        # Handle bold text
        stripped = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', stripped)
        
        # Handle italics
        stripped = re.sub(r'\*(.*?)\*', r'<em>\1</em>', stripped)

        # Handle headings
        if stripped.startswith("### "):
            result_html.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            result_html.append(f"<h3>{stripped[3:]}</h3>")
        elif stripped.startswith("# "):
            result_html.append(f"<h2>{stripped[2:]}</h2>")

        # Handle unordered lists
        elif stripped.startswith("- "):
            if not in_ul:
                result_html.append("<ul>")
                in_ul = True
            result_html.append(f"<li>{stripped[2:]}</li>")

        # Handle ordered lists
        elif re.match(r"^\d+\.\s", stripped):
            if not in_ol:
                result_html.append("<ol>")
                in_ol = True
            item = re.sub(r"^\d+\.\s", "", stripped)
            result_html.append(f"<li>{item}</li>")

        # Handle key-value pairs
        elif ":" in stripped and not stripped.startswith("http") and not re.match(r'^https?://', stripped):
            key, value = stripped.split(":", 1)
            result_html.append(f"<p><strong>{key.strip()}</strong>: {value.strip()}</p>")

        # Handle empty lines
        elif not stripped:
            if in_ul:
                result_html.append("</ul>")
                in_ul = False
            if in_ol:
                result_html.append("</ol>")
                in_ol = False
            result_html.append("<br>")

        # Handle regular paragraphs
        else:
            result_html.append(f"<p>{stripped}</p>")

    # Close any open lists
    if in_ul:
        result_html.append("</ul>")
    if in_ol:
        result_html.append("</ol>")
    
    # The output should be valid HTML (not escaped)
    return "\n".join(result_html)










# def format_response_as_html(text: str) -> str:
#     """
#     Convert markdown-formatted text to HTML.
#     Handles headings, lists, key-value pairs, and paragraphs.
#     """
#     lines = text.strip().splitlines()
#     html = []
#     in_ul = False
#     in_ol = False

#     for line in lines:
#         stripped = line.strip()

#         if stripped.startswith("**") and stripped.endswith("**"):
#             stripped = stripped[2:-2].strip()

#         if stripped.startswith("### "):
#             html.append(f"<h3>{escape(stripped[4:])}</h3>")
#         elif stripped.startswith("## "):
#             html.append(f"<h2>{escape(stripped[3:])}</h2>")
#         elif stripped.startswith("# "):
#             html.append(f"<h1>{escape(stripped[2:])}</h1>")

#         elif stripped.startswith("- "):
#             if not in_ul:
#                 html.append("<ul>")
#                 in_ul = True
#             html.append(f"<li>{escape(stripped[2:])}</li>")

#         elif re.match(r"^\d+\.\s", stripped):
#             if not in_ol:
#                 html.append("<ol>")
#                 in_ol = True
#             item = re.sub(r"^\d+\.\s", "", stripped)
#             html.append(f"<li>{escape(item)}</li>")

#         elif ":" in stripped and not stripped.startswith("http"):
#             key, value = stripped.split(":", 1)
#             html.append(f"<p><strong>{escape(key.strip())}:</strong> {escape(value.strip())}</p>")

#         elif not stripped:
#             if in_ul:
#                 html.append("</ul>")
#                 in_ul = False
#             if in_ol:
#                 html.append("</ol>")
#                 in_ol = False
#             html.append("<br>")

#         else:
#             html.append(f"<p>{escape(stripped)}</p>")

#     if in_ul:
#         html.append("</ul>")
#     if in_ol:
#         html.append("</ol>")

#     return "\n".join(html)