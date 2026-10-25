import pytest
from backend.research.tavily_research import callback_documentation_excerpt

@pytest.mark.parametrize('name',['parse_qsl','parse\\_qsl','**parse\\_qsl**','`parse_qsl`'])
def test_escaped_function_signature_keeps_retrieved_text(name):
    raw=f'urllib.parse.{name}(qs, keep\\_blank\\_values=False) The default means blank values are ignored. urllib.parse.urlunparse(parts) Other function.'
    section=callback_documentation_excerpt(raw)
    assert section is not None and 'blank values are ignored' in section
    assert 'Other function' not in section
    if '\\_' in name:assert '\\_' in section

def test_navigation_match_does_not_hide_later_real_section():
    raw='parse_qsl() urlunparse() NAVIGATION urllib.parse.parse\\_qsl(qs) A true value indicates that blanks should be retained. urllib.parse.urlunparse(parts) NEXT'
    section=callback_documentation_excerpt(raw)
    assert section.startswith('urllib.parse.parse\\_qsl')
    assert 'NAVIGATION' not in section

def test_signature_without_behavior_is_not_usable_documentation():
    assert callback_documentation_excerpt('parse_qsl(qs, keep_blank_values=False) urlunparse(parts)') is None


def test_behavior_after_long_markdown_signature_is_not_truncated_away():
    raw = "urllib.parse.parse_qsl(qs) " + ("[parameter](https://docs.python.org/" + "x" * 90 + ") ") * 22 + "The default false value indicates that blank values are ignored. urllib.parse.urlunparse(parts) NEXT"
    excerpt = callback_documentation_excerpt(raw)
    assert excerpt and "blank values are ignored" in excerpt
    assert len(excerpt) <= 1800 and "NEXT" not in excerpt
    assert excerpt in raw

def test_markdown_emphasis_in_behavior_paragraph():
    raw = "parse_qsl(qs) The blank **values** are ignored. urlunparse(parts)"
    assert "blank **values**" in callback_documentation_excerpt(raw)
