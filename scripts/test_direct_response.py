import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.runtime import Agent, load_config


def test_greeting_response_can_finish_without_action_loop():
    agent = Agent(load_config())

    assert agent._is_direct_response("oneword", "Short direct response.")


def test_clarifying_question_can_finish_without_action_loop():
    agent = Agent(load_config())

    assert agent._is_direct_response(
        "ambiguous multi word request",
        "Which target should I use?",
    )


def test_long_direct_answer_can_finish_without_action_loop():
    agent = Agent(load_config())
    response = "\n".join(
        f"- Capability area {i}: can perform local automation tasks."
        for i in range(20)
    )

    assert agent._is_direct_response("WHAT U CAN DO?", response)


def test_action_plan_is_not_treated_as_direct_response():
    agent = Agent(load_config())

    assert not agent._is_direct_response(
        "write a report",
        'OBJECTIVE: Write a report\nACTION: {"tool": "write_file", "args": {}}',
    )
