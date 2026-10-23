import json
import subprocess
from pathlib import Path
from unittest.mock import patch
import pytest
from backend.scoring.trust_engine import TrustEngine, TestResults as Results
from backend.research.evidence import build_test_evidence
from backend.sandbox.docker_runner import DockerSandbox
from backend.tools.repository import RepositoryTools

@pytest.mark.parametrize('adversarial', [Results(0,0,0),Results(1,0,0,1),Results(3,2,0),Results(1,2,0)])
def test_errors_and_missing_tests_are_inconclusive(adversarial):
    result=TrustEngine().calculate(Results(3,3,0),adversarial)
    assert result.status.value=='INCONCLUSIVE' and result.score is None

def test_assertion_and_corrected_control_policy():
    engine=TrustEngine()
    assert engine.calculate(Results(3,3,0),Results(2,1,1)).status.value=='REJECTED'
    assert engine.calculate(Results(3,3,0),Results(2,1,1),validation_problem='Corrected control failed').status.value=='INCONCLUSIVE'
    assert engine.calculate(Results(3,3,0),Results(2,2,0)).status.value=='PASSED_CHECKS'

def test_citations_reject_fabricated_quotes_and_ids():
    source={'id':'S1','url':'https://docs.python.org/3.11/library/urllib.parse.html','content':'A sufficiently long exact excerpt about URL parsing.'}
    tests=[{'code':'def test_url():\n    assert True','source_refs':[{'source_id':'S1','quote':'sufficiently long exact excerpt'},{'source_id':'S1','quote':'fabricated source words do not occur'},{'source_id':'S9','quote':'sufficiently long exact excerpt'}]}]
    report=build_test_evidence(tests,[source])
    assert len(report[0]['sources'])==1 and report[0]['claimed_reference_count']==3

def test_writes_are_limited_to_selected_source(tmp_path):
    (tmp_path/'shop.py').write_text('x=1')
    tools=RepositoryTools(str(tmp_path),{'shop.py'})
    for filename in ['conftest.py','test_shop.py','other.py']:
        assert tools.write_file(filename,'raise Exception()').startswith('ERROR')
    with pytest.raises(ValueError):tools.write_file('../escape.py','pass')
    assert 'Successfully' in tools.write_file('shop.py','x=2')

def test_timeout_removes_container(tmp_path):
    commands=[]
    def runner(command,**kwargs):
        commands.append(command)
        if command[1]=='run':raise subprocess.TimeoutExpired(command,60)
        return subprocess.CompletedProcess(command,0,'','')
    with patch('backend.sandbox.docker_runner.subprocess.run',side_effect=runner):
        result=DockerSandbox(str(tmp_path)).run_tests('test_case.py')
    assert result['summary']['error']==1 and commands[-1][1:3]==['rm','-f']
    assert '--read-only' in commands[0] and '65532:65532' in commands[0]

def test_collection_failure_is_not_silently_passed(tmp_path):
    def runner(command,**kwargs):
        if command[1]=='run':
            mount=next(command[i+1] for i,x in enumerate(command) if x=='--mount' and 'target=/reports' in command[i+1])
            out=Path(mount.split('source=')[1].split(',')[0])/'report.json'
            out.write_text(json.dumps({'summary':{'total':0},'collectors':[{'nodeid':'test_bad.py','outcome':'failed','longrepr':'SyntaxError: invalid syntax'}]}))
            return subprocess.CompletedProcess(command,2,'','')
        return subprocess.CompletedProcess(command,0,'','')
    with patch('backend.sandbox.docker_runner.subprocess.run',side_effect=runner):
        result=DockerSandbox(str(tmp_path)).run_tests()
    assert result['summary']['error']>=1 and 'SyntaxError' in result['tests'][0]['error']
