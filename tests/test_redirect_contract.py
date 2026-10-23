import runpy
from backend.scenarios import get_scenario

def test_reference_allows_normalized_dot_segments():
    scenario=get_scenario('redirect')
    fixed=runpy.run_path(str(scenario.reference_file))['safe_redirect']
    assert fixed('/./account')=='https://app.example/account'
    assert fixed('/account?tab=settings#section')=='https://app.example/account?tab=settings#section'

def test_origin_boundary_distinguishes_buggy_and_corrected():
    scenario=get_scenario('redirect')
    buggy=runpy.run_path(str(scenario.repo_path/scenario.source_file))['safe_redirect']
    fixed=runpy.run_path(str(scenario.reference_file))['safe_redirect']
    assert buggy('//external.example/account')=='https://external.example/account'
    assert fixed('//external.example/account')=='https://app.example/'
