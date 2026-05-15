import contextlib
import copy
import io
import os
import shutil

from core.runtime import Agent
from core.runtime_config import load_config


class ScriptedClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.model = "scripted-complex-stress-model"
        self.provider = "mock"

    def chat(self, messages, system=""):
        self.calls.append(
            {
                "messages": [dict(m) for m in messages],
                "system": system,
            }
        )
        if not self.responses:
            return "FINAL ANSWER: scripted response queue exhausted"
        return self.responses.pop(0)

    def list_models(self):
        return [self.model]


class RecordingTools:
    def __init__(self, observations):
        self.observations = dict(observations)
        self.calls = []
        self._canvas = ""
        self._notepad = []
        self.shadow_mode = False
        self.term = type("Term", (), {"system_info": lambda self: "stress-test-system"})()
        self.ui = type("UI", (), {"send_notification": lambda self, title, message: None})()

    def get_symbol(self, tool_name):
        return "*"

    def tool_descriptions(self):
        return (
            "file_exists: Check if path exists. Args: path\n"
            "read_file: Read file. Args: path\n"
            "write_file: Write file. Args: path, content"
        )

    def call(self, tool_name, args):
        self.calls.append((tool_name, dict(args or {})))
        key = (tool_name, tuple(sorted((args or {}).items())))
        return self.observations.get(key, self.observations.get(tool_name, "OK"))


def make_agent(tmp_workspace):
    cfg = copy.deepcopy(load_config())
    cfg["agent"]["workspace"] = str(tmp_workspace)
    cfg["agent"]["provider"] = "ollama"
    cfg["agent"]["verbose_thinking"] = False
    cfg["memory"]["backend"] = "json"
    cfg["memory"]["path"] = os.path.join(str(tmp_workspace), "memory.json")
    cfg["logging"]["audit_enabled"] = False
    cfg["autonomy"]["task_tracking"] = False
    cfg["rules"]["require_confirm_destructive"] = False
    agent = Agent(cfg)
    agent.max_iter = 8
    return agent


def run_quiet(agent, task):
    with contextlib.redirect_stdout(io.StringIO()) as out:
        agent.run(task)
    return out.getvalue()


def test_complex_fragmented_checklist_waits_for_remaining_lines(tmp_path):
    agent = make_agent(tmp_path)
    agent.client = ScriptedClient(["FINAL ANSWER: should not be called"])

    output = run_quiet(agent, "Then verify all of these:")

    assert "Send the remaining lines/items" in output
    assert agent.client.calls == []


def test_complex_batched_action_executes_only_first_and_warns_next_turn(tmp_path):
    agent = make_agent(tmp_path)
    agent.client = ScriptedClient(
        [
            (
                "OBJECTIVE: Stress batching.\n"
                "ACTION: {\"tool\": \"file_exists\", \"args\": {\"path\": \"one.txt\"}}\n"
                "ACTION: {\"tool\": \"write_file\", \"args\": {\"path\": \"two.txt\", \"content\": \"bad batch\"}}"
            ),
            "FINAL ANSWER: stopped after single action warning",
        ]
    )
    agent.tools = RecordingTools({"file_exists": "False"})

    run_quiet(agent, "Run a complex task but accidentally batch two tool calls.")

    assert agent.tools.calls == [("file_exists", {"path": "one.txt"})]
    second_turn = "\n".join(
        m["content"] for m in agent.client.calls[1]["messages"] if m["role"] == "user"
    )
    assert "Only the first tool was executed" in second_turn
    assert "VERIFICATION_FAILED" in second_turn


def test_complex_save_failure_forces_strategy_change_context(tmp_path):
    agent = make_agent(tmp_path)
    target = r"C:\AgenticOs\workspace\deep_mouse_vision_test.txt"
    agent.client = ScriptedClient(
        [
            (
                "OBJECTIVE: Verify Notepad save.\n"
                f"ACTION: {{\"tool\": \"file_exists\", \"args\": {{\"path\": \"{target}\"}}}}"
            ),
            "FINAL ANSWER: I switched strategy after the failed verification.",
        ]
    )
    agent.tools = RecordingTools(
        {
            (
                "file_exists",
                (("path", target),),
            ): "False"
        }
    )

    run_quiet(
        agent,
        (
            "Save a Notepad file through the Save dialog, then verify file_exists "
            "and read_file for the exact target path."
        ),
    )

    second_turn = "\n".join(
        m["content"] for m in agent.client.calls[1]["messages"] if m["role"] == "user"
    )
    assert "VERIFICATION_FAILED" in second_turn
    assert "Do not repeat the same save attempt" in second_turn
    assert "switch strategy" in second_turn


def test_complex_end_to_end_report_write_verify_read_final(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    agent = make_agent(workspace)
    report_path = workspace / "reports" / "complex_gauntlet.md"
    agent.client = ScriptedClient(
        [
            (
                "OBJECTIVE: Create a verified report.\n"
                "ACTION: {\"tool\": \"write_file\", \"args\": {\"path\": \"reports/complex_gauntlet.md\", "
                "\"content\": \"# Complex Gauntlet\\n\\n- alpha\\n- beta\\n- gamma\\n\"}}"
            ),
            (
                "CURRENT_STEP: Confirm file exists.\n"
                "ACTION: {\"tool\": \"file_exists\", \"args\": {\"path\": \"reports/complex_gauntlet.md\"}}"
            ),
            (
                "CURRENT_STEP: Verify content, not only existence.\n"
                "ACTION: {\"tool\": \"read_file\", \"args\": {\"path\": \"reports/complex_gauntlet.md\"}}"
            ),
            "FINAL ANSWER: Complex gauntlet report saved and content verified.",
        ]
    )

    output = run_quiet(
        agent,
        (
            "Create a markdown report with three bullets, verify existence, read it back, "
            "and only then finalize."
        ),
    )

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "# Complex Gauntlet" in content
    assert "- gamma" in content
    assert "Complex gauntlet report saved and content verified" in output

    shutil.rmtree(workspace / "reports", ignore_errors=True)
