from callbacks import parse_callback_query


def test_normal_callback():
    assert parse_callback_query("event=paid&amount=2500") == [("event", "paid"), ("amount", "2500")]


def test_repeated_names_keep_order():
    assert parse_callback_query("tag=red&tag=blue") == [("tag", "red"), ("tag", "blue")]


def test_form_encoding():
    assert parse_callback_query("name=Ada+Lovelace&note=a%2Bb") == [("name", "Ada Lovelace"), ("note", "a+b")]
