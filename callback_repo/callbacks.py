from urllib.parse import parse_qsl


def parse_callback_query(raw_query: str) -> list[tuple[str, str]]:
    """Decode callback form fields into ordered (name, value) pairs.

    The downstream signature pipeline needs every submitted field, in order,
    including repetitions. Interpret input as application/x-www-form-urlencoded
    according to Python 3.11. Inputs are valid query strings, not full URLs.
    Do not sort or discard submitted fields. Non-string inputs are outside
    this helper's contract. This helper does not itself verify signatures.
    """
    return parse_qsl(raw_query)
