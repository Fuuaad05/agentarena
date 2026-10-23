from auth import is_session_valid

def test_exact_expiration():
    assert is_session_valid(100, 100) is False
