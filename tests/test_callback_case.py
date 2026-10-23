import runpy
from backend.scenarios import get_scenario

def test_callback_original_cases_pass_both_variants():
    scenario=get_scenario('callback')
    for path in [scenario.repo_path/scenario.source_file,scenario.reference_file]:
        parse=runpy.run_path(str(path))['parse_callback_query']
        assert parse('a=one&a=two')==[('a','one'),('a','two')]
        assert parse('name=Ada+Lovelace&note=a%2Bb')==[('name','Ada Lovelace'),('note','a+b')]

def test_optional_field_loss_distinguishes_reference():
    scenario=get_scenario('callback')
    buggy=runpy.run_path(str(scenario.repo_path/scenario.source_file))['parse_callback_query']
    fixed=runpy.run_path(str(scenario.reference_file))['parse_callback_query']
    assert buggy('event=paid&metadata=')==[('event','paid')]
    assert fixed('event=paid&metadata=')==[('event','paid'),('metadata','')]

def test_symptom_report_does_not_supply_the_parser_option():
    report=get_scenario('callback').default_bug_report
    assert 'keep_blank_values' not in report and 'metadata=' not in report
