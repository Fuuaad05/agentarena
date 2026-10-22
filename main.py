from backend.pipeline import AgentArenaPipeline


BUG_REPORT = """
Customers report that applying a 0% discount produces an
incorrect total. Other discount percentages appear to work.
"""


pipeline = AgentArenaPipeline(
    repo_path="playground_repo"
)

pipeline.run(BUG_REPORT)