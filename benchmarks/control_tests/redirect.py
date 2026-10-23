from redirects import safe_redirect

def test_network_path_cannot_replace_origin():
    assert safe_redirect("//external.example/account") == "https://app.example/"

def test_local_path_preserved():
    assert safe_redirect("/account") == "https://app.example/account"
