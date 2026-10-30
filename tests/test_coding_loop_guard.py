import json
from types import SimpleNamespace
import backend.agents.coding_agent as module


def response(name=None, **args):
    calls = [SimpleNamespace(id='call', function=SimpleNamespace(name=name, arguments=json.dumps(args)))] if name else []
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(tool_calls=calls, content='Finished' if not name else None))])


def run_case(monkeypatch, tmp_path, edit=None):
    source = 'def fee(w):\n    return 5 if w < 1 else 10\n'
    (tmp_path/'shipping.py').write_text(source)
    (tmp_path/'test_shipping.py').write_text('sentinel')
    responses = [response('run_tests'), response('run_tests')]
    if edit is not None:
        responses.append(response('write_file', path='shipping.py', content=edit))
    responses.extend([response('run_tests'), response()])
    iterator = iter(responses)
    prompts, runs = [], []
    class FakeLLM:
        def chat(self, messages, tools):
            prompts.append(list(messages))
            return next(iterator)
    monkeypatch.setattr(module, 'NebiusLLM', FakeLLM)
    monkeypatch.setattr(module.RepositoryTools, 'run_tests', lambda self: runs.append(1) or 'Exit code: 0\n4 passed')
    agent = module.CodingAgent(str(tmp_path), allowed_files={'shipping.py'})
    return agent.run('Include 1 kg'), runs, prompts, agent


def test_loop_stops_without_reexecuting_tests(monkeypatch, tmp_path):
    summary, runs, prompts, agent = run_case(monkeypatch, tmp_path)
    assert summary.startswith('Repair incomplete:')
    assert len(runs) == 1
    assert agent.trace[-1]['result_excerpt'].startswith('NOT EXECUTED:')
    assert any(isinstance(m, dict) and 'Do not repeat run_tests' in m.get('content', '') for m in prompts[2])


def test_real_edit_allows_retest(monkeypatch, tmp_path):
    summary, runs, _, _ = run_case(monkeypatch, tmp_path, 'def fee(w):\n    return 5 if w <= 1 else 10\n')
    assert summary == 'Finished'
    assert len(runs) == 2
    assert '<= 1' in (tmp_path/'shipping.py').read_text()
    assert (tmp_path/'test_shipping.py').read_text() == 'sentinel'


def test_noop_write_cannot_reset_guard(monkeypatch, tmp_path):
    summary, runs, _, _ = run_case(monkeypatch, tmp_path, 'def fee(w):\n    return 5 if w < 1 else 10\n')
    assert summary.startswith('Repair incomplete:')
    assert len(runs) == 1
