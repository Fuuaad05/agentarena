"""Fresh proposals remain scoped, syntactically valid, and independently testable."""
import json
from types import SimpleNamespace
import pytest
import backend.agents.coding_agent as module


def make_agent(monkeypatch, tmp_path, proposals, finish='tool_calls'):
    (tmp_path/'source.py').write_text('def add(a, b): return a - b\n')
    (tmp_path/'test_source.py').write_text('test sentinel')
    requests, executions = [], []
    class FakeLLM:
        def chat(self, **kwargs):
            requests.append(kwargs)
            calls = [SimpleNamespace(function=SimpleNamespace(
                name=name, arguments=json.dumps(args))) for name, args in proposals]
            return SimpleNamespace(choices=[SimpleNamespace(
                finish_reason=finish, message=SimpleNamespace(tool_calls=calls))])
    monkeypatch.setattr(module, 'NebiusLLM', FakeLLM)
    monkeypatch.setattr(module.RepositoryTools, 'run_tests',
                        lambda self: executions.append(1) or 'Exit code: 0\n3 passed')
    agent = module.CodingAgent(str(tmp_path), allowed_files={'source.py'})
    return agent, requests, executions


def test_applies_model_proposal_and_executes_tests(monkeypatch, tmp_path):
    agent, requests, executions = make_agent(monkeypatch, tmp_path, [
        ('write_file', {'path': 'source.py', 'content': 'def add(a, b): return a + b\n'})])
    result = agent._propose_patch('Return the sum', [
        {'tool': 'run_tests', 'result': 'Exit code: 0; baseline passed'}], 5)
    assert 'Fresh model patch proposal applied' in result
    assert executions == [1]
    assert 'a + b' in (tmp_path/'source.py').read_text()
    assert (tmp_path/'test_source.py').read_text() == 'test sentinel'
    assert len(requests) == 1
    assert [t['function']['name'] for t in requests[0]['tools']] == ['write_file']
    assert [m['role'] for m in requests[0]['messages']] == ['system', 'user']
    context = json.loads(requests[0]['messages'][1]['content'])
    assert context['observed_test_results'] == ['Exit code: 0; baseline passed']
    assert 'curated' not in context


@pytest.mark.parametrize('name,args,finish', [
    ('write_file', {'path': '../outside.py', 'content': 'x=1'}, 'tool_calls'),
    ('write_file', {'path': 'test_source.py', 'content': 'x=1'}, 'tool_calls'),
    ('write_file', {'path': 'source.py', 'content': 'def broken('}, 'tool_calls'),
    ('run_command', {'command': 'anything'}, 'tool_calls'),
    ('write_file', {'path': 'source.py', 'content': 'x=1'}, 'length'),
])
def test_rejects_invalid_proposals_without_writes_or_tests(monkeypatch, tmp_path, name, args, finish):
    agent, _, executions = make_agent(monkeypatch, tmp_path, [(name, args)], finish)
    assert agent._propose_patch('Sum', [], 5).startswith('Repair incomplete:')
    assert (tmp_path/'source.py').read_text() == 'def add(a, b): return a - b\n'
    assert (tmp_path/'test_source.py').read_text() == 'test sentinel'
    assert not executions
