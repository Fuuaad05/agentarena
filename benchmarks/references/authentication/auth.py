def is_session_valid(
    current_time: int,
    expires_at: int,
) -> bool:
    """
    Return True if a session is still valid.

    A session expires at its expiration timestamp.
    """

    if current_time >= expires_at:
        return False

    return True