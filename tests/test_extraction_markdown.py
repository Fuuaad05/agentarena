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
