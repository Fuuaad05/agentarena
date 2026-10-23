from redirects import safe_redirect

def test_local_path():
    assert safe_redirect("/account") == "https://app.example/account"

def test_rejects_absolute_external():
    assert safe_redirect("https://external.example/") == "https://app.example/"

def test_query_string():
    assert safe_redirect("/account?tab=settings") == "https://app.example/account?tab=settings"
