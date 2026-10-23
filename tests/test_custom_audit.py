from types import SimpleNamespace
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
import backend.api as api
import backend.limits as limits
import backend.pipeline as pipeline
from backend.custom_audit import run_custom_audit, validate_custom_input
from test_pipeline_controls import TrustedLocalRunner

@pytest.mark.parametrize('source,tests',[
 ('',''),('def broken(','') ,('x=1','this is not valid python !'),('x=1','x=2'),('x'*20001,'')])
def test_invalid_custom_input(source,tests):
    with pytest.raises((ValueError,SyntaxError)):validate_custom_input(source,tests)

@pytest.mark.parametrize('source,expected',[
 ('def add(a,b):\n    return a-b\n','failures_reproduced'),
 ('def add(a,b):\n    return a+b\n','checks_passed')])
@pytest.mark.parametrize('existing_tests',['','from solution import add\ndef test_existing():\n    assert add(0,0)==0\n'])
def test_custom_reports_are_unvalidated_and_not_publicly_saved(monkeypatch,source,expected,existing_tests):
    class Verifier:
        llm=SimpleNamespace(model='test-double',usage={})
        def generate_tests(self,**kwargs):
            assert 'from solution import *' in kwargs['test_imports']
            return {'analysis':'Fixture','tests':[{'code':'def test_add():\n    assert add(2,3)==5'}]}
    monkeypatch.setattr(pipeline,'DockerSandbox',TrustedLocalRunner)
    monkeypatch.setattr(pipeline,'AdversarialVerifier',Verifier)
    with patch('backend.pipeline.save_investigation') as save:
        report=run_custom_audit(source,existing_tests,'Add both numbers')
    save.assert_not_called()
    assert report['custom_audit'] and report['assessment']==expected
    assert report['status']=='INCONCLUSIVE' and report['evidence_score'] is None
    assert report['reference_validation'] is None and 'investigation_id' not in report
    assert report['original_tests_label']==('Provided tests' if existing_tests else 'Import smoke check')
    assert report['events']
    assert "Custom code audit" in report["verification_limits"]
    assert "Curated scenario" not in report["verification_limits"]

def test_source_is_parsed_without_host_execution(tmp_path):
    marker=tmp_path/'must-not-exist'
    validate_custom_input(f"open({str(marker)!r},'w').write('executed')")
    assert not marker.exists()

def test_custom_endpoints_enforce_opt_in_audit_mode_and_auth(monkeypatch):
    client=TestClient(api.app)
    monkeypatch.setenv('AGENTARENA_API_TOKEN','test-token')
    monkeypatch.setenv('DAILY_RUN_LIMIT','20')
    limits._active=False;limits._count=0;limits._recent=[];limits._day=''
    payload={'scenario_id':'custom','mode':'audit','source_code':'def add(a,b):\n return a+b','bug_report':'Add numbers'}
    monkeypatch.delenv('ENABLE_CUSTOM_AUDIT',raising=False)
    assert client.post('/api/investigate',json=payload).status_code==503
    monkeypatch.setenv('ENABLE_CUSTOM_AUDIT','true')
    for endpoint in ['/api/investigate','/api/investigate/stream']:
        assert client.post(endpoint,json=payload).status_code==401
        assert client.post(endpoint,json={**payload,'mode':'repair'},headers={'X-Arena-Token':'test-token'}).status_code==400
    with patch('backend.api.run_custom_audit',return_value={'custom_audit':True,'status':'INCONCLUSIVE'}) as run:
        response=client.post('/api/investigate',json=payload,headers={'X-Arena-Token':'test-token'})
    assert response.status_code==200 and response.json()['custom_audit']
    assert run.call_args.args[:3]==(payload['source_code'],'',payload['bug_report'])
    assert not limits._active
    with patch('backend.api.run_custom_audit',return_value={'custom_audit':True,'status':'INCONCLUSIVE'}):
        streamed=client.post('/api/investigate/stream',json=payload,headers={'X-Arena-Token':'test-token'})
    assert '"complete"' in streamed.text and not limits._active
