from pathlib import Path

from backend.llm.nebius import NebiusLLM


repo = Path("playground_repo")

shop_code = (repo / "shop.py").read_text(encoding="utf-8")
test_code = (repo / "test_shop.py").read_text(encoding="utf-8")

bug_report = """
Customers report that applying a 0% discount produces an
incorrect total. Other discount percentages appear to work.
"""

system_prompt = """
You are the coding agent for AgentArena.

Your job is to investigate software bugs using evidence.

Do not assume the bug report tells you the root cause.
Examine the provided source code and tests.

Return these three sections:
1. ROOT CAUSE
2. PROPOSED FIX
3. WHY THE FIX IS CORRECT

Be concise.
"""

user_prompt = """
BUG REPORT:
{bug_report}

SOURCE FILE: shop.py

{shop_code}

TEST FILE: test_shop.py

{test_code}

Investigate the bug.
""".format(
    bug_report=bug_report,
    shop_code=shop_code,
    test_code=test_code,
)

llm = NebiusLLM()

print("AgentArena: investigating bug...\n")

result = llm.chat(
    system_prompt=system_prompt,
    user_prompt=user_prompt,
)

print(result)