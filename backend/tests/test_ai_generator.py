import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from ai_generator import AIGenerator


class FakeToolManager:
    def __init__(self):
        self.calls = []

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        return "tool result"


class AIGeneratorToolCallTests(unittest.TestCase):
    def make_generator(self):
        return AIGenerator(
            api_key="test-key",
            model="test-model",
            base_url="https://example.test/chat/completions",
        )

    def test_generate_response_sends_tools_and_executes_course_search_tool_call(self):
        generator = self.make_generator()
        generator._create_chat_completion = Mock(
            side_effect=[
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "search_course_content",
                                "arguments": (
                                    '{"query":"tool use",'
                                    '"course_name":"Building Towards Computer Use with Anthropic",'
                                    '"lesson_number":6}'
                                ),
                            },
                        }
                    ],
                },
                {"role": "assistant", "content": "final answer"},
            ]
        )
        manager = FakeToolManager()
        tools = [
            {
                "name": "search_course_content",
                "description": "Search course content",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            }
        ]

        answer = generator.generate_response(
            "What is tool use?",
            tools=tools,
            tool_manager=manager,
        )

        self.assertEqual(answer, "final answer")
        first_payload = generator._create_chat_completion.call_args_list[0].args[0]
        self.assertEqual(first_payload["tool_choice"], "auto")
        self.assertEqual(
            first_payload["tools"][0]["function"]["name"],
            "search_course_content",
        )
        self.assertEqual(
            manager.calls,
            [
                (
                    "search_course_content",
                    {
                        "query": "tool use",
                        "course_name": "Building Towards Computer Use with Anthropic",
                        "lesson_number": 6,
                    },
                )
            ],
        )
        final_payload = generator._create_chat_completion.call_args_list[1].args[0]
        self.assertNotIn("tools", final_payload)
        self.assertEqual(final_payload["messages"][-1]["role"], "tool")
        self.assertEqual(final_payload["messages"][-1]["content"], "tool result")

    def test_malformed_tool_arguments_execute_with_empty_kwargs(self):
        generator = self.make_generator()
        generator._create_chat_completion = Mock(
            side_effect=[
                {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "function": {
                                "name": "search_course_content",
                                "arguments": "{not json",
                            },
                        }
                    ],
                },
                {"role": "assistant", "content": "final answer"},
            ]
        )
        manager = FakeToolManager()

        answer = generator.generate_response(
            "question",
            tools=[{"name": "search_course_content", "input_schema": {"type": "object"}}],
            tool_manager=manager,
        )

        self.assertEqual(answer, "final answer")
        self.assertEqual(manager.calls, [("search_course_content", {})])


if __name__ == "__main__":
    unittest.main()
