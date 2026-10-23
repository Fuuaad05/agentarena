import json
from types import SimpleNamespace
import pytest
from backend.agents.verifier import AdversarialVerifier

def response(content, reason='stop'):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content),finish_reason=reason)])

def valid():
    return json.dumps({'tests':[{'code':'def test_boundary():\n    assert True'}]})

@pytest.mark.parametrize('first',[response('{"analysis":"broken'),response(valid(),'length'),response(json.dumps({'tests':[{'code':'def invalid('}]}))])
def test_invalid_output_is_retried(first):
    calls=[]
    replies=iter([first,response(valid())])
    verifier=object.__new__(AdversarialVerifier)
    def chat(**kwargs):calls.append(kwargs);return next(replies)
    verifier.llm=SimpleNamespace(chat=chat)
    assert verifier.generate_tests('bug','source','tests')['tests']
    assert len(calls)==2

def test_invalid_output_stops_after_three_attempts():
    calls=[]
    verifier=object.__new__(AdversarialVerifier)
    def chat(**kwargs):calls.append(kwargs);return response('broken')
    verifier.llm=SimpleNamespace(chat=chat)
    with pytest.raises(RuntimeError,match='after 3 attempts'):
        verifier.generate_tests('bug','source','tests')
    assert len(calls)==3


def test_timeout_is_retried_and_logged(monkeypatch):
    import httpx
    from openai import APITimeoutError
    monkeypatch.setattr('backend.agents.verifier.time.sleep', lambda seconds:None)
    attempts=[];events=[]
    verifier=object.__new__(AdversarialVerifier)
    verifier.progress_callback=events.append
    def chat(**kwargs):
        attempts.append(kwargs)
        if len(attempts)==1:raise APITimeoutError(request=httpx.Request('POST','https://example.invalid'))
        return response(valid())
    verifier.llm=SimpleNamespace(chat=chat)
    assert verifier.generate_tests('bug','source','tests')['tests']
    assert len(attempts)==2 and attempts[0]['timeout']<=75
    assert any('APITimeoutError' in message for message in events)

def test_authentication_error_is_not_retried():
    import httpx
    from openai import AuthenticationError
    attempts=[]
    verifier=object.__new__(AdversarialVerifier)
    def chat(**kwargs):
        attempts.append(kwargs)
        raise AuthenticationError('Invalid key',response=httpx.Response(401,request=httpx.Request('POST','https://example.invalid')),body=None)
    verifier.llm=SimpleNamespace(chat=chat)
    with pytest.raises(AuthenticationError):verifier.generate_tests('bug','source','tests')
    assert len(attempts)==1
