from auth import is_session_valid


def test_session_before_expiration():
    assert is_session_valid(90, 100) is True


def test_session_after_expiration():
    assert is_session_valid(110, 100) is False


def test_session_well_before_expiration():
    assert is_session_valid(50, 100) is True