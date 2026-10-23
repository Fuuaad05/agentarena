"""Check text provenance without inferring semantic support or inventing citations."""
import ast
import re


def normalise(text):
    return re.sub(r"\s+", " ", str(text)).strip().casefold()


def build_test_evidence(tests, sources, specification=""):
    by_id = {s.get("id", f"S{i}"): s for i, s in enumerate(sources, 1)}
    output = []
    for test in tests:
        names = [n.name for n in ast.parse(test["code"]).body if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")]
        claimed = test.get("source_refs", [])
        refs, checks, specification_refs = [], [], []
        if not isinstance(claimed, list):
            claimed = [claimed]
        for index, ref in enumerate(claimed[:10]):
            source_id = ref.get("source_id") if isinstance(ref, dict) else None
            quote = ref.get("quote") if isinstance(ref, dict) else None
            source = by_id.get(source_id) if isinstance(source_id, str) else None
            if source_id == "BUG_REPORT" and isinstance(quote, str) and 16 <= len(quote.strip()) <= 400 and normalise(quote) in normalise(specification):
                specification_refs.append({"quote": quote.strip(), "verification": "Matched supplied specification; not an external citation."})
                continue
            if index >= 3:
                reason = "reference_limit_exceeded"
            elif not isinstance(ref, dict) or not isinstance(quote, str):
                reason = "invalid_reference_structure"
            elif not isinstance(source_id, str) or not source_id:
                reason = "missing_source_id"
            elif not source:
                reason = "unknown_source_id"
            elif len(quote.strip()) < 16:
                reason = "quote_too_short"
            elif len(quote.strip()) > 400:
                reason = "quote_too_long"
            elif normalise(quote) not in normalise(source.get("content", "")):
                reason = "quote_not_found_in_supplied_excerpt"
            else:
                reason = "excerpt_matched"
                refs.append({"source_id": source_id, "url": source["url"], "title": source.get("title", ""),
                             "quote": quote.strip(), "verification": "Excerpt match after whitespace/case normalization; semantic support requires review."})
            checks.append({"source_id": str(source_id or "")[:100],
                           "claimed_quote": quote[:400] if isinstance(quote, str) else "",
                           "status": "accepted" if reason == "excerpt_matched" else "rejected", "reason": reason})
        for name in names:
            output.append({"test_name": name, "rationale": str(test.get("rationale", ""))[:600],
                           "expected_behavior": str(test.get("expected_behavior", ""))[:600],
                           "specification_refs": specification_refs, "sources": refs, "provenance_status": "excerpt_matched" if refs else "no_verified_source",
                           "claimed_reference_count": len(claimed), "citation_checks": checks,
                           "omitted_reference_count": max(0, len(claimed) - 10)})
    return output
