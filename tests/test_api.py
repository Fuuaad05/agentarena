from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
import backend.limits as limits
from backend.api import app
@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv('AGENTARENA_API_TOKEN','test-token')
    monkeypatch.setenv('DAILY_RUN_LIMIT','20')
    limits._active=False;limits._count=0;limits._day='';limits._recent=[]
    return TestClient(app)
PAYLOAD={'scenario_id':'shipping','bug_report':'Check the boundary','mode':'audit'}
HEADERS={'X-Arena-Token':'test-token'}

def test_unauthorised_runs_never_call_pipeline(client):
    with patch('backend.api.run_pipeline') as pipeline:
        assert client.post('/api/investigate',json=PAYLOAD).status_code==401
        assert client.post('/api/investigate/stream',json=PAYLOAD).status_code==401
        pipeline.assert_not_called()

def test_stream_and_standard_release_slot(client):
    with patch('backend.api.run_pipeline',return_value={'status':'PASSED_CHECKS'}):
        assert client.post('/api/investigate',json=PAYLOAD,headers=HEADERS).status_code==200
        response=client.post('/api/investigate/stream',json=PAYLOAD,headers=HEADERS)
        assert '"complete"' in response.text
    assert not limits._active

def test_failures_release_slot(client):
    with patch('backend.api.run_pipeline',side_effect=RuntimeError('test error')):
        assert client.post('/api/investigate',json=PAYLOAD,headers=HEADERS).status_code==500
    assert not limits._active

def test_concurrency_and_daily_limits(client,monkeypatch):
    limits._active=True
    assert client.post('/api/investigate',json=PAYLOAD,headers=HEADERS).status_code==429
    limits._active=False;monkeypatch.setenv('DAILY_RUN_LIMIT','0')
    assert client.post('/api/investigate',json=PAYLOAD,headers=HEADERS).status_code==429

def test_unknown_scenario_rejected_before_run(client):
    assert client.post('/api/investigate',json={**PAYLOAD,'scenario_id':'../../escape'},headers=HEADERS).status_code==400
