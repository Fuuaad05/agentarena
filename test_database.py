from backend.database.storage import (
    initialize_database,
    save_investigation,
    list_investigations,
    get_investigation,
)


initialize_database()

sample_report = {
    "project": "AgentArena",
    "timestamp": "2026-10-12T12:00:00Z",
    "status": "PASSED_CHECKS",
    "evidence_score": 100,
    "bug_report": "Test database persistence",
    "original_tests": {
        "total": 3,
        "passed": 3,
        "failed": 0,
    },
}

investigation_id = save_investigation(sample_report)

print("Saved investigation:", investigation_id)

history = list_investigations()

print("\nInvestigation history:")
for item in history:
    print(
        item["id"],
        item["status"],
        item["evidence_score"],
    )

saved = get_investigation(investigation_id)

print("\nRetrieved report:")
print(saved)