import pytest
from backend.verification.classifier import FailureClassifier

@pytest.mark.parametrize('path,phase,kind,expected',[
 ('redirects.py','failed','AttributeError','PRODUCTION_EXCEPTION'),
 ('/workspace/redirects.py','failed','TypeError','PRODUCTION_EXCEPTION'),
 ('test_adversarial.py','failed','AttributeError','UNKNOWN'),
 ('elsewhere/redirects.py','failed','AttributeError','UNKNOWN'),
 ('redirects.py','passed','AttributeError','UNKNOWN'),
 ('redirects.py','failed','MemoryError','EXECUTION_ERROR'),
])
def test_runtime_witness_requires_structured_production_location(path,phase,kind,expected):
    result=FailureClassifier({'redirects.py'}).classify({'name':'test_case','error':kind+': failure','call_outcome':phase,'crash':{'path':path,'message':kind+': failure'}})
    assert result.category.value==expected

def test_exception_text_alone_is_not_a_production_witness():
    result=FailureClassifier({'redirects.py'}).classify({'name':'test_case','error':'redirects.py:7: AttributeError'})
    assert result.category.value=='UNKNOWN'
