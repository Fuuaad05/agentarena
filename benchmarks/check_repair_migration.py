"""Isolated live repair probe; does not alter fixtures or shared history.

Calls the configured model. A curated boundary check is added ONLY after the
agent finishes, so it is not available to guide its patch proposal.
"""
import difflib
import json
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.agents.coding_agent import CodingAgent
from backend.sandbox.docker_runner import DockerSandbox


def main():
    with tempfile.TemporaryDirectory() as directory:
        repo = Path(directory) / 'repository'
        shutil.copytree(ROOT / 'shipping_repo', repo,
                        ignore=shutil.ignore_patterns('__pycache__', '.pytest_cache', 'test_adversarial.py'))
        before = (repo / 'shipping.py').read_text()
        agent = CodingAgent(str(repo), max_steps=12, allowed_files={'shipping.py'})
        summary = agent.run(
            'Some customers report being charged the wrong shipping fee for packages near '
            'the 1 kg boundary. Shipping should cost $5 for weights up to and including 1 kg.')
        after = (repo / 'shipping.py').read_text()
        original = DockerSandbox(str(repo)).run_tests('test_shipping.py')
        shutil.copyfile(ROOT / 'benchmarks/control_tests/shipping.py', repo / 'test_control.py')
        boundary = DockerSandbox(str(repo)).run_tests('test_control.py')
        passed = before != after and original.get('success') and boundary.get('success')
        print(json.dumps({
            'model': agent.llm.model, 'source_changed': before != after,
            'summary': summary, 'agent_trace': agent.trace,
            'patch': ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
                                                fromfile='before/shipping.py', tofile='after/shipping.py')),
            'original_tests': original, 'withheld_curated_boundary_check': boundary,
            'migration_probe_passed': bool(passed),
            'limitations': 'One live fixture probe, not proof of general repair reliability or a model benchmark.',
        }, indent=2))
        return 0 if passed else 1


if __name__ == '__main__':
    sys.exit(main())
