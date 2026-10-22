from pathlib import Path
from backend.agents.coding_agent import CodingAgent

adversarial_file = Path(
    "playground_repo/test_adversarial.py"
)

if adversarial_file.exists():
    adversarial_file.unlink()
    
BUG_REPORT = """
Customers report that applying a 0% discount produces an
incorrect total. Other discount percentages appear to work.
"""


agent = CodingAgent(
    repo_path="playground_repo",
    max_steps=12,
)

agent.run(BUG_REPORT)