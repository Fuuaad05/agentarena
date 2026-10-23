from urllib.parse import urljoin

BASE = "https://app.example/"

def safe_redirect(target: str) -> str:
    """Return a same-origin redirect; invalid destinations fall back to BASE."""
    if not target.startswith("/"):
        return BASE
    return urljoin(BASE, target)
