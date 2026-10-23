import pytest
from backend.research.evidence import build_test_evidence
from backend.research.tavily_research import callback_documentation_excerpt

SOURCE={'id':'S1','url':'https://docs.python.org/3.11/library/urllib.parse.html','content':'The blank values are ignored by default and must be explicitly retained.'}

@pytest.mark.parametrize('claim,reason',[
 ({'source_id':'S1','quote':'blank values are ignored by default'},'excerpt_matched'),
 ({'source_id':'S9','quote':'blank values are ignored by default'},'unknown_source_id'),
 ({'quote':'blank values are ignored by default'},'missing_source_id'),
 ({'source_id':'S1','quote':'blank'},'quote_too_short'),
 ({'source_id':'S1','quote':'This paraphrase does not occur in the retrieved text.'},'quote_not_found_in_supplied_excerpt'),
 ({'source_id':'S1','quote':'x'*401},'quote_too_long'),
 ('invalid citation','invalid_reference_structure'),
])
def test_citation_checks_preserve_rejected_claim_and_reason(claim,reason):
    evidence=build_test_evidence([{'code':'def test_case():\n    assert True','source_refs':[claim]}],[SOURCE])[0]
    check=evidence['citation_checks'][0]
    assert check['reason']==reason
    assert len(evidence['sources'])==(1 if reason=='excerpt_matched' else 0)
    if isinstance(claim,dict):assert check['claimed_quote']==claim['quote'][:400]

def test_parse_qsl_section_does_not_take_parse_qs_paragraph():
    raw=('urllib.parse.parse_qs(qs) DICTIONARY SECTION blank values ignored. '
         'urllib.parse.**parse_qsl**(qs, keep_blank_values=False) LIST SECTION blank values ignored. '
         'urllib.parse.urlunparse(parts) NEXT SECTION')
    section=callback_documentation_excerpt(raw)
    assert 'LIST SECTION' in section and 'DICTIONARY SECTION' not in section and 'NEXT SECTION' not in section

def test_missing_parse_qsl_section_is_not_silently_substituted():
    assert callback_documentation_excerpt('urllib.parse.parse_qs(qs) blank values ignored.') is None


def test_bug_report_reference_is_separate_from_external_citations():
    spec = "add(a, b) must return the sum of two numbers."
    test = {"code": "def test_add():\n    assert True", "source_refs": [{"source_id": "BUG_REPORT", "quote": spec}]}
    evidence = build_test_evidence([test], [], spec)[0]
    assert evidence["sources"] == [] and evidence["citation_checks"] == []
    assert evidence["specification_refs"][0]["quote"] == spec
    assert build_test_evidence([test], [], "Different specification")[0]["citation_checks"][0]["status"] == "rejected"
