import shutil
import tempfile

from contextlib import contextmanager
from pathlib import Path


@contextmanager
def investigation_workspace(source_repo: str):
    """
    Create an isolated temporary copy of a repository
    for a single investigation.
    """

    source = Path(source_repo).resolve()

    if not source.is_dir():
        raise ValueError(
            f"Source repository does not exist: {source}"
        )

    with tempfile.TemporaryDirectory(
        prefix="agentarena_"
    ) as temp_dir:

        workspace = Path(temp_dir) / "repository"

        shutil.copytree(
            source,
            workspace,
            ignore=shutil.ignore_patterns(
                "__pycache__",
                ".pytest_cache",
                ".agentarena_report.json",
                ".agentarena_docker_report.json",
                "test_adversarial.py",
            ),
        )

        yield workspace