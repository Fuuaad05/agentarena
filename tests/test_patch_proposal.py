import json
from types import SimpleNamespace
import pytest
import backend.agents.coding_agent as module

SOURCE = 'def add(a, b):\n    """Keep this docstring unchanged."""\n    return a - b\n'


def edit(path='source.py', old='a - b', new='a + b', name='propose_edit'):
    return SimpleNamespace(function=SimpleNamespace(name=name, arguments=json.dumps({
        'path': path, 'old_text': old, 'new_text': new})))


def setup_agent(monkeypatch, tmp_path, batches, finish='tool_calls'):
    (tmp_path/'source.py').write_text(SOURCE)
    (tmp_path/'test_source.py').write_text('test sentinel')
    requests, runs = [], []
    class FakeLLM:
        def chat(self, **kwargs):
            requests.append(kwargs)
            calls = batches[min(len(requests)-1, len(batches)-1)]
            return SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish,
                message=SimpleNamespace(tool_calls=calls))])
    monkeypatch.setattr(module, 'NebiusLLM', FakeLLM)
    monkeypatch.setattr(module.RepositoryTools, 'run_tests', lambda self: runs.append(1) or 'Exit code: 0; tests passed')
    return module.CodingAgent(str(tmp_path), allowed_files={'source.py'}), requests, runs


def test_applies_small_edit_without_rewriting_docstring(monkeypatch, tmp_path):
    agent, requests, runs = setup_agent(monkeypatch, tmp_path, [[edit()]])
    assert agent._propose_patch('Sum', [], 5).startswith('Fresh model patch proposal applied')
    assert (tmp_path/'source.py').read_text() == SOURCE.replace('a - b', 'a + b')
    assert (tmp_path/'test_source.py').read_text() == 'test sentinel'
    assert runs == [1]
    assert [t['function']['name'] for t in requests[0]['tools']] == ['propose_edit']
    assert [m['role'] for m in requests[0]['messages']] == ['system', 'user']


@pytest.mark.parametrize('bad', [
    edit(path='../outside.py'), edit(path='test_source.py'),
    edit(old='missing text'), edit(old=''), edit(new='a - b'),
    edit(new='('), edit(name='run_command'),
])
def test_invalid_edits_are_bounded_and_never_written(monkeypatch, tmp_path, bad):
    agent, requests, runs = setup_agent(monkeypatch, tmp_path, [[bad]])
    assert agent._propose_patch('Sum', [], 5).startswith('Repair incomplete:')
    assert len(requests) == 2
    assert not runs
    assert (tmp_path/'source.py').read_text() == SOURCE
    assert (tmp_path/'test_source.py').read_text() == 'test sentinel'
    assert any(t['tool'] == 'patch_validation' for t in agent.trace)


def test_ambiguous_match_is_rejected(monkeypatch, tmp_path):
    agent, requests, runs = setup_agent(monkeypatch, tmp_path, [[edit(old='a', new='x')]])
    assert 'match exactly once' in agent._propose_patch('Sum', [], 5)
    assert not runs


def test_syntax_feedback_can_recover_once(monkeypatch, tmp_path):
    agent, requests, runs = setup_agent(monkeypatch, tmp_path, [[edit(new='(')], [edit()]])
    assert agent._propose_patch('Sum', [], 5).startswith('Fresh model patch proposal applied')
    assert len(requests) == 2
    assert 'SyntaxError' in requests[1]['messages'][-1]['content']
    assert runs == [1]


def test_valid_edit_is_not_written_if_another_edit_is_invalid(monkeypatch, tmp_path):
    agent, _, runs = setup_agent(monkeypatch, tmp_path, [[edit(), edit(path='test_source.py')]])
    assert agent._propose_patch('Sum', [], 5).startswith('Repair incomplete:')
    assert (tmp_path/'source.py').read_text() == SOURCE
    assert not runs


def test_truncated_proposal_cannot_write(monkeypatch, tmp_path):
    agent, _, runs = setup_agent(monkeypatch, tmp_path, [[edit()]], finish='length')
    assert 'truncated' in agent._propose_patch('Sum', [], 5)
    assert not runs
    assert (tmp_path/'source.py').read_text() == SOURCE
