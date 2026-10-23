"""Single-file, audit-only input. Source is never imported by the API process."""
import ast
import tempfile
from pathlib import Path
from backend.pipeline import AgentArenaPipeline
from backend.scenarios import Scenario

MAX_SOURCE = 20000
MAX_TESTS = 12000

def validate_custom_input(source, tests=''):
    if not isinstance(source,str) or not source.strip() or len(source)>MAX_SOURCE:
        raise ValueError('Paste a Python module containing at most 20,000 characters.')
    ast.parse(source,filename='solution.py')
    if len(tests)>MAX_TESTS:raise ValueError('Existing tests must be at most 12,000 characters.')
    if tests.strip():
        parsed=ast.parse(tests,filename='test_solution.py')
        if not any(isinstance(n,ast.FunctionDef) and n.name.startswith('test_') for n in ast.walk(parsed)):
            raise ValueError('Existing tests must contain at least one pytest test_ function.')

class CustomAuditPipeline(AgentArenaPipeline):
    def __init__(self,*args,has_existing_tests=False,**kwargs):
        super().__init__(*args,**kwargs)
        self.has_existing_tests=has_existing_tests

    def save_report(self,report):
        # Never place arbitrary user reports or inputs in the shared public history.
        execution=report.get('execution') or {}
        checks=[execution.get('original') or {},execution.get('adversarial') or {}]
        usable=all(c.get('summary',{}).get('total',0)>0 and not c.get('summary',{}).get('error',0)
                   and not c.get('summary',{}).get('skipped',0) and not c.get('execution_error') and c.get('summary',{}).get('total',0)==c.get('summary',{}).get('passed',0)+c.get('summary',{}).get('failed',0) for c in checks)
        failures=any(c.get('summary',{}).get('failed',0)>0 for c in checks)
        assessment=('failures_reproduced' if failures else 'checks_passed') if usable else 'inconclusive'
        report.update(custom_audit=True,assessment=assessment,status='INCONCLUSIVE',evidence_score=None,
                      verification_limits="Custom code audit; no corrected reference is available. Generated expectations require review and passing tests do not prove correctness or security.",
                      reference_validation=None,events=list(self.events.history),
                      original_tests_label='Provided tests' if self.has_existing_tests else 'Import smoke check',
                      explanation=('Executed tests reproduced failures. Review whether the expectations match your specification.' if assessment=='failures_reproduced' else
                                   'All executed checks passed. This does not prove correctness.' if assessment=='checks_passed' else
                                   report.get('explanation','Verification could not complete.')) +
                                  ' No corrected reference is available for custom code; this result is unvalidated. It is not saved in shared history.')
        report.pop('investigation_id',None)
        return report

def run_custom_audit(source, tests, bug_report, event_callback=None):
    validate_custom_input(source,tests)
    with tempfile.TemporaryDirectory(prefix='arena_custom_') as directory:
        root=Path(directory)
        (root/'solution.py').write_text(source,encoding='utf-8')
        has_tests=bool(tests.strip())
        (root/'test_solution.py').write_text(tests if has_tests else 'def test_module_imports():\n    import solution\n',encoding='utf-8')
        scenario=Scenario(id='custom',name='Your Python code',description='Single-file custom audit',repo_path=root,
                          source_file='solution.py',test_file='test_solution.py',test_imports='import solution\nfrom solution import *',default_bug_report=bug_report)
        return CustomAuditPipeline(str(root),scenario=scenario,event_callback=event_callback,
                                   enable_research=False,has_existing_tests=has_tests).run(bug_report,mode='audit')
