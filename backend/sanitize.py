"""
HTML sanitising for rich-text fields written by suppliers (Tiptap editor output).

Everything outside the allow-list below is stripped, including scripts, event
handler attributes, inline styles, iframes and javascript: URLs.
"""
import nh3

ALLOWED_TAGS = {
    "p", "br", "hr", "span", "div",
    "strong", "b", "em", "i", "u", "s", "strike", "sub", "sup", "mark",
    "code", "pre", "blockquote",
    "h1", "h2", "h3", "h4", "h5", "h6",
    "ul", "ol", "li",
    "a", "img",
    "table", "thead", "tbody", "tfoot", "tr", "th", "td", "colgroup", "col", "caption",
}

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title", "target"},
    "img": {"src", "alt", "title", "width", "height"},
    "td": {"colspan", "rowspan", "colwidth"},
    "th": {"colspan", "rowspan", "colwidth"},
    "col": {"span"},
    "ol": {"start"},
}

ALLOWED_URL_SCHEMES = {"http", "https", "mailto", "tel"}


def sanitize_rich_text(value):
    """Return `value` with only allow-listed HTML kept. Non-strings pass through."""
    if not isinstance(value, str) or not value:
        return value
    return nh3.clean(
        value,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
        link_rel="noopener noreferrer nofollow",
    )
