from types import SimpleNamespace
import backend.database.storage as storage
import backend.pipeline as pipeline
from backend.events import EventEmitter
from backend.llm.nebius import NebiusLLM
from backend.scenarios import get_scenario

def test_progress_and_failure_survive_saved_report(monkeypatch,tmp_path):
    path=tmp_path/'history.db'
    monkeypatch.setattr(storage,'DATABASE_PATH',path)
    monkeypatch.setattr(pipeline,'DATABASE_PATH',path)
    arena=pipeline.AgentArenaPipeline(str(get_scenario('redirect').repo_path))
    arena.emit('adversarial','running','Verifier request 1/3 started')
    arena.emit('adversarial','failed','Verifier failed: APITimeoutError')
    report=arena.save_report({'status':'INCONCLUSIVE','bug_report':'test','error':'APITimeoutError'})
    saved=storage.get_investigation(report['investigation_id'])
    assert saved['investigation_id']==report['investigation_id']
    assert saved['events'][1]['message']=='Verifier failed: APITimeoutError'
    assert saved['error']=='APITimeoutError'

def test_legacy_report_keeps_identity_without_fabricated_events(monkeypatch,tmp_path):
    monkeypatch.setattr(storage,'DATABASE_PATH',tmp_path/'history.db')
    ident=storage.save_investigation({'status':'INCONCLUSIVE','error':'Request timed out.'})
    saved=storage.get_investigation(ident)
    assert saved['investigation_id']==ident and 'events' not in saved

def test_verifier_timeout_option_reaches_sdk():
    seen=[]
    def create(**kwargs):seen.append(kwargs);return SimpleNamespace(usage=None)
    llm=object.__new__(NebiusLLM);llm.model='test';llm.usage={}
    llm.client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    llm.chat([],timeout=75)
    assert seen[0]['timeout']==75
