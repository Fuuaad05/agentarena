from callbacks import parse_callback_query


def test_submitted_empty_values_are_not_discarded():
    assert parse_callback_query("event=paid&metadata=&tag=one&tag=") == [
        ("event", "paid"), ("metadata", ""), ("tag", "one"), ("tag", "")]
