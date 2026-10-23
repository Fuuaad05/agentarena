from urllib.parse import urljoin, urlsplit

BASE = "https://app.example/"

def safe_redirect(target: str) -> str:
    """Accept local root-relative paths and return only this application's origin."""
    if not isinstance(target, str) or not target.startswith("/"):
        return BASE
    if "\\" in target or any(ord(ch) <= 32 or ord(ch) == 127 for ch in target):
        return BASE
    try:
        parts = urlsplit(target)
        if parts.scheme or parts.netloc:
            return BASE
        candidate = urljoin(BASE, target)
        parsed = urlsplit(candidate)
        if parsed.scheme != "https" or parsed.netloc != "app.example":
            return BASE
        return candidate
    except ValueError:
        return BASE
