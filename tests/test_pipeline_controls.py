"""Integration checks use trusted test snippets and local pytest, not a Docker/model substitute in production."""
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
import pytest
import backend.pipeline as pipeline_module
from backend.pipeline import AgentArenaPipeline
from backend.scenarios import get_scenario
from backend.workspace import investigation_workspace

class TrustedLocalRunner:
    def __init__(self,repo_path):self.root=Path(repo_path)
    def run_tests(self,test_file=None):
        run=subprocess.run([sys.executable,'-m','pytest','-q','-p','no:cacheprovider','--json-report','--json-report-file=qa-report.json',test_file],cwd=self.root,capture_output=True,text=True,timeout=20)
        data=json.loads((self.root/'qa-report.json').read_text())
        summary={key:data['summary'].get(key,0) for key in ['total','passed','failed','error','skipped']}
        return {'success':run.returncode==0,'exit_code':run.returncode,'summary':summary,'tests':[{'name':t['nodeid'],'outcome':t['outcome'],'error':t.get('call',{}).get('longrepr',''),'call_outcome':t.get('call',{}).get('outcome'),'crash':t.get('call',{}).get('crash',{})} for t in data['tests']],'output':run.stdout}

@pytest.mark.parametrize('corrected,code,expected',[
    (False,'def test_boundary():\n    assert calculate_shipping(1.0) == 5','REJECTED'),
    (True,'def test_boundary():\n    assert calculate_shipping(1.0) == 5','PASSED_CHECKS'),
    (False,'def test_bad_expectation():\n    assert calculate_shipping(2) == 999','INCONCLUSIVE'),
    (False,'def test_bad_name():\n    assert unknown_function()','INCONCLUSIVE'),
])
def test_pipeline_validates_generated_suite_on_corrected_control(monkeypatch,corrected,code,expected):
    class Verifier:
        llm=SimpleNamespace(model='test-double',usage={})
        def generate_tests(self,**kwargs):
            assert 'reference' not in kwargs
            return {'analysis':'QA fixture','tests':[{'code':code}],'research_insights':[]}
    monkeypatch.setattr(pipeline_module,'DockerSandbox',TrustedLocalRunner)
    monkeypatch.setattr(pipeline_module,'AdversarialVerifier',Verifier)
    monkeypatch.setattr(AgentArenaPipeline,'save_report',lambda self,report: report)
    scenario=get_scenario('shipping')
    with investigation_workspace(str(scenario.repo_path)) as workspace:
        if corrected:(Path(workspace)/scenario.source_file).write_text(scenario.reference_file.read_text())
        report=AgentArenaPipeline(str(workspace),scenario=scenario,enable_research=False).run('Shipping up to 1 kg costs 5',mode='audit')
    assert report['status']==expected
    assert 'generated_test_source' in report
    assert report['reference_validation']['kind']=='curated_corrected_control'

def test_original_execution_failure_stops_before_paid_calls(monkeypatch):
    class BrokenRunner:
        def __init__(self,*args):pass
        def run_tests(self,**kwargs):
            return {'success':False,'execution_error':'Docker CLI timed out','summary':{'total':0,'passed':0,'failed':0,'error':1}}
    def forbidden(*args,**kwargs):raise AssertionError('Paid component must not start')
    monkeypatch.setattr(pipeline_module,'DockerSandbox',BrokenRunner)
    monkeypatch.setattr(pipeline_module,'AdversarialVerifier',forbidden)
    monkeypatch.setattr(pipeline_module,'TavilyResearch',forbidden)
    monkeypatch.setattr(AgentArenaPipeline,'save_report',lambda self,report:report)
    scenario=get_scenario('redirect')
    with investigation_workspace(str(scenario.repo_path)) as workspace:
        report=AgentArenaPipeline(str(workspace),scenario=scenario).run('Check redirect',mode='audit')
    assert report['status']=='INCONCLUSIVE'
    assert report['execution']['original']['execution_error']=='Docker CLI timed out'
    assert report['research']['status']=='not_run'


@pytest.mark.parametrize('include_origin_assertion,expected', [(True,'REJECTED'),(False,'REJECTED')])
def test_redirect_runtime_failure_does_not_erase_control_validated_assertion(monkeypatch,include_origin_assertion,expected):
    snippets=[{'code': 'def test_non_string():\n    assert safe_redirect(123) == "https://app.example/"'}]
    if include_origin_assertion:
        snippets.append({'code': 'def test_origin():\n    assert safe_redirect("//evil.com/path") == "https://app.example/"'})
    class Verifier:
        llm=SimpleNamespace(model='test-double',usage={})
        def generate_tests(self,**kwargs):return {'analysis':'Regression fixture','tests':snippets,'research_insights':[]}
    monkeypatch.setattr(pipeline_module,'DockerSandbox',TrustedLocalRunner)
    monkeypatch.setattr(pipeline_module,'AdversarialVerifier',Verifier)
    monkeypatch.setattr(AgentArenaPipeline,'save_report',lambda self,report:report)
    scenario=get_scenario('redirect')
    with investigation_workspace(str(scenario.repo_path)) as workspace:
        report=AgentArenaPipeline(str(workspace),scenario=scenario,enable_research=False).run(scenario.default_bug_report,mode='audit')
    assert report['status']==expected
    assert report['reference_validation']['success']
    assert any(f['category']=='PRODUCTION_EXCEPTION' for f in report['failures'])
