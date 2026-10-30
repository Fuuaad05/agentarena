import hashlib
import json

from backend.llm.nebius import NebiusLLM
from backend.tools.repository import RepositoryTools


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files available in the repository.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a text file from the repository.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Repository-relative file path.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": (
                "Replace a repository file with new content. "
                "Use this to implement fixes."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                    },
                    "content": {
                        "type": "string",
                    },
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "run_tests",
            "description": (
                "Run the repository test suite and return "
                "the test output and exit code."
            ),
            "parameters": {
                "type": "object",
                "properties": {},
            },
        },
    },
]


SYSTEM_PROMPT = """
You are the autonomous coding agent in AgentArena.

You receive a software bug report and access to a repository
through tools.

Follow this investigation protocol:

1. Inspect relevant repository files.
2. BEFORE modifying code, run the existing tests to establish
   evidence of the failure.
3. Identify the root cause based on source code and test output.
4. Make the smallest reasonable change to production code.
5. Run the tests after the modification.
6. If tests fail, continue investigating.
7. Finish only after verification succeeds.

Never invent tools. You may ONLY use tools explicitly provided
to you.

Do not invent file contents. Read a file before modifying it.
Test files are read-only. Do not create or modify ANY test file.
Existing tests may all pass because they miss the reported bug. Passing baseline
checks does not resolve the bug report. Inspect the production boundary/logic
against the stated requirements and edit production source when warranted.
Do not fabricate failing baseline evidence if the original tests pass.

When verification succeeds, respond with a concise summary:
- Root cause
- Files changed
- Before: failing test evidence
- After: passing test evidence
"""


class CodingAgent:
    def __init__(
        self,
        repo_path: str,
        max_steps: int = 12,
        allowed_files=None,
    ):
        self.llm = NebiusLLM()
        self.repo = RepositoryTools(repo_path, allowed_files=allowed_files)
        self.max_steps = max_steps
        self.trace = []

    def execute_tool(self, name: str, arguments: dict) -> str:
        if name == "list_files":
            return self.repo.list_files()

        if name == "read_file":
            return self.repo.read_file(arguments["path"])

        if name == "write_file":
            return self.repo.write_file(
                arguments["path"],
                arguments["content"],
            )

        if name == "run_tests":
            return self.repo.run_tests()

        return f"ERROR: Unknown tool: {name}"

    def _source_fingerprint(self):
        """Ignore pytest reports/caches; detect actual Python source changes."""
        digest = hashlib.sha256()
        for path in sorted(self.repo.root.rglob("*.py")):
            relative = path.relative_to(self.repo.root)
            if any(part.startswith(".") or part == "__pycache__" for part in relative.parts):
                continue
            digest.update(str(relative).encode())
            digest.update(b"\0")
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def run(self, bug_report: str):
        messages = [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"BUG REPORT:\n{bug_report}",
            },
        ]

        if self.repo.allowed_files:
            messages[1]["content"] += "\nWritable production files: " + ", ".join(sorted(self.repo.allowed_files)) + ". Test files cannot be edited."
        empty_responses = 0
        last_test_fingerprint = None
        repeated_tests = 0
        for step in range(1, self.max_steps + 1):
            print(f"\n--- Agent step {step} ---")

            response = self.llm.chat(
                messages=messages,
                tools=TOOLS,
            )

            message = response.choices[0].message

            # The model has decided it is finished.
            if not message.tool_calls:
                if not (message.content or "").strip() and empty_responses < 1 and step < self.max_steps:
                    empty_responses += 1
                    messages.append({"role": "user", "content": "Your last response was empty. Continue from the observed tool results. Test files are read-only; fix the production source if the bug report warrants it, run the existing tests, and provide an honest summary. If no fix was made, explicitly say so and why."})
                    continue
                final_answer = message.content or "Coding agent returned no final summary; inspect observed actions and patch diff."
                print("\nAgent finished:")
                print(final_answer)

                return final_answer

            messages.append(message)

            for tool_call in message.tool_calls:
                name = tool_call.function.name

                try:
                    arguments = json.loads(
                        tool_call.function.arguments or "{}"
                    )
                except json.JSONDecodeError:
                    arguments = {}

                print(f"Tool: {name}")

                if arguments:
                    safe_args = {
                        key: (
                            "<file content>"
                            if key == "content"
                            else value
                        )
                        for key, value in arguments.items()
                    }

                    print(f"Arguments: {safe_args}")

                stop_for_loop = False
                try:
                    fingerprint = self._source_fingerprint() if name == "run_tests" else None
                    if name == "run_tests" and fingerprint == last_test_fingerprint:
                        repeated_tests += 1
                        stop_for_loop = repeated_tests >= 2
                        result = (
                            "NOT EXECUTED: Python source is unchanged since the previous test run. "
                            "Repeating the same suite adds no evidence. Baseline tests can miss the "
                            "reported bug. Reassess the source against the bug report; make a minimal "
                            "production change only if warranted, then run tests. If no change is "
                            "warranted, explain why and finish honestly."
                        )
                    else:
                        result = self.execute_tool(name, arguments)
                        if name == "run_tests":
                            last_test_fingerprint = fingerprint
                            repeated_tests = 0
                except Exception as error:
                    result = f"ERROR: {error}"

                self.trace.append({"step": step, "tool": name,
                                   "path": arguments.get("path"),
                                   "result_excerpt": result[:600] if name != "read_file" else "Source file read; content omitted from trace."})
                print("Result:")
                print(result[:1500])

                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    }
                )
                if stop_for_loop:
                    return (
                        "Repair incomplete: the coding agent repeatedly requested tests without "
                        "changing Python source, despite a recovery instruction. The repeated "
                        "requests were not executed. Inspect the observed actions and patch diff; "
                        "independent verification still evaluates the current source."
                    )

            # Send guidance after all results in a tool-call batch are supplied.
            if any(
                isinstance(item, dict) and item.get("role") == "tool"
                and item.get("content", "").startswith("NOT EXECUTED:")
                for item in messages[-len(message.tool_calls):]
            ):
                messages.append({
                    "role": "user",
                    "content": "The unchanged tests have already run. Reassess the reported defect "
                    "using the source and requirements. Do not repeat run_tests before an actual "
                    "source change. Either implement a justified fix or explain why you cannot.",
                })

        result = (
            f"Agent stopped after reaching "
            f"{self.max_steps} steps."
        )

        print(result)
        return result