from pathlib import Path

from backend.workspace import investigation_workspace


source = Path("auth_repo/auth.py")

original_content = source.read_text(
    encoding="utf-8"
)

print("Original repository exists:", source.exists())

with investigation_workspace("auth_repo") as workspace:

    copied_file = workspace / "auth.py"

    print("Temporary workspace:", workspace)

    print(
        "Copied source exists:",
        copied_file.exists()
    )

    copied_file.write_text(
        "# Modified inside temporary workspace",
        encoding="utf-8"
    )

    print(
        "Original unchanged:",
        source.read_text(
            encoding="utf-8"
        ) == original_content
    )

print(
    "Temporary workspace deleted:",
    not workspace.exists()
)