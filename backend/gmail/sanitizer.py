"""
HTML sanitizer for safe rendering of original email bodies (Section 5.F & 14.11).

KEY CONCEPT: Email HTML Sanitization
-------------------------------------
Emails from university systems and third parties often contain tracking pixels,
injected scripts, iframes, and styling that could break the host UI or execute
malicious JavaScript (XSS). This module strips all dangerous elements and attributes,
neutralizes javascript: URIs, and enforces safe external link behaviors.
"""

from bs4 import BeautifulSoup
import re

# Allowed safe HTML tags for email rendering
ALLOWED_TAGS = {
    "a", "abbr", "acronym", "b", "blockquote", "br", "caption", "cite", "code",
    "col", "colgroup", "dd", "del", "div", "dl", "dt", "em", "h1", "h2", "h3",
    "h4", "h5", "h6", "hr", "i", "img", "ins", "kbd", "li", "ol", "p", "pre",
    "q", "s", "samp", "small", "span", "strike", "strong", "sub", "sup", "table",
    "tbody", "td", "tfoot", "th", "thead", "tr", "tt", "u", "ul", "var"
}

# Dangerous tags that must be completely removed along with their content
DANGEROUS_TAGS = {
    "script", "style", "iframe", "object", "embed", "applet", "form",
    "input", "button", "textarea", "select", "link", "meta", "base"
}

# Allowed attributes per tag
ALLOWED_ATTRS = {
    "*": ["class", "id", "title", "dir", "lang"],
    "a": ["href", "title", "target", "rel"],
    "img": ["src", "alt", "title", "width", "height"],
    "table": ["border", "cellpadding", "cellspacing", "width", "align"],
    "td": ["align", "valign", "width", "colspan", "rowspan"],
    "th": ["align", "valign", "width", "colspan", "rowspan"],
    "div": ["align"],
    "p": ["align"],
}

SAFE_URL_SCHEMES = ("http://", "https://", "mailto:", "tel:", "cid:")


def sanitize_email_html(raw_html: str) -> str:
    """
    Sanitize raw email HTML to ensure safe display in browser:
    - Removes all <script>, <style>, <iframe>, <form> tags.
    - Strips all on* event handlers (e.g. onerror, onclick, onload).
    - Neutralizes javascript: and data: URLs.
    - Adds target="_blank" and rel="noopener noreferrer" to all links.
    - Preserves readable layout, tables, formatting, and images.
    """
    if not raw_html:
        return ""

    soup = BeautifulSoup(raw_html, "html.parser")

    # 1. Completely decompose dangerous tags
    for tag in soup.find_all(DANGEROUS_TAGS):
        tag.decompose()

    # 2. Iterate through all remaining tags
    for tag in list(soup.find_all(True)):
        if tag.name not in ALLOWED_TAGS:
            # Unwrap tag but keep its text content
            tag.unwrap()
            continue

        # Inspect and filter attributes
        attrs = dict(tag.attrs)
        tag.attrs.clear()

        for attr_name, attr_val in attrs.items():
            attr_name_lower = attr_name.lower()

            # Strip any event handler (onclick, onload, onerror, etc.)
            if attr_name_lower.startswith("on"):
                continue

            # Check if attribute is allowed for this tag or globally
            allowed_for_tag = ALLOWED_ATTRS.get(tag.name, [])
            allowed_global = ALLOWED_ATTRS.get("*", [])

            if attr_name_lower not in allowed_for_tag and attr_name_lower not in allowed_global:
                continue

            val_str = " ".join(attr_val) if isinstance(attr_val, list) else str(attr_val)

            # Check URLs in href and src
            if attr_name_lower in ("href", "src"):
                cleaned_val = val_str.strip().lower()
                # Block javascript:, vbscript:, data:text/html
                if cleaned_val.startswith(("javascript:", "vbscript:", "data:text/html")):
                    continue
                # For images or links, require safe scheme
                if not any(cleaned_val.startswith(scheme) for scheme in SAFE_URL_SCHEMES) and not cleaned_val.startswith(("/", "#")):
                    continue

            tag[attr_name] = val_str

        # Ensure all <a> tags open securely in new tab
        if tag.name == "a":
            tag["target"] = "_blank"
            tag["rel"] = "noopener noreferrer"

    return str(soup)
