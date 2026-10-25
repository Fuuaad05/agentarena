from types import SimpleNamespace
import json
import backend.agents.coding_agent as module


def test_empty_final_recovers_without_allowing_test_edits(monkeypatch, tmp_path):
    (tmp_path/'shipping.py').write_text('def fee(w):\n    return 5 if w < 1 else 10\n')
    (tmp_path/'test_shipping.py').write_text('original test sentinel')
    def response(calls=None, content=None):
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=calls,content=content))])
    def call(path, content):
        return SimpleNamespace(id='call',function=SimpleNamespace(name='write_file',arguments=json.dumps({'path':path,'content':content})))
    responses=iter([
        response([call('test_shipping.py','must not overwrite')]),
        response(content=''),
        response([call('shipping.py','def fee(w):\n    return 5 if w <= 1 else 10\n')]),
        response(content='Changed shipping.py to include the boundary. Original tests were not modified.'),
    ])
    prompts=[]
    class FakeLLM:
        def chat(self, messages, tools):
            prompts.append([m.copy() if isinstance(m,dict) else m for m in messages])
            return next(responses)
    monkeypatch.setattr(module,'NebiusLLM',FakeLLM)
    agent=module.CodingAgent(str(tmp_path),allowed_files={'shipping.py'})
    summary=agent.run('Fee is 5 up to and including 1 kg')
    assert 'shipping.py' in summary
    assert (tmp_path/'test_shipping.py').read_text()=='original test sentinel'
    assert '<= 1' in (tmp_path/'shipping.py').read_text()
    assert 'ERROR:' in agent.trace[0]['result_excerpt']
    assert 'Writable production files: shipping.py' in prompts[0][1]['content']
    assert any(isinstance(m,dict) and 'last response was empty' in m.get('content','') for m in prompts[2])


def test_empty_final_retry_is_bounded(monkeypatch,tmp_path):
    class FakeLLM:
        def __init__(self):self.calls=0
        def chat(self,**kwargs):
            self.calls+=1
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=None,content=None))])
    monkeypatch.setattr(module,'NebiusLLM',FakeLLM)
    agent=module.CodingAgent(str(tmp_path))
    assert 'no final summary' in agent.run('Investigate')
    assert agent.llm.calls==2
