import sys
import unittest
from pathlib import Path
from unittest.mock import Mock

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from ai_generator import AIGenerator


class FakeToolManager:
    def __init__(self, results=None, fail_on_call=None):
        self.calls = []
        self.results = results or ["tool result"]
        self.fail_on_call = fail_on_call

    def execute_tool(self, tool_name, **kwargs):
        self.calls.append((tool_name, kwargs))
        if self.fail_on_call == len(self.calls):
            raise RuntimeError("tool failed")
        result_index = min(len(self.calls) - 1, len(self.results) - 1)
        return self.results[result_index]


class AIGeneratorToolCallTests(unittest.TestCase):
    def make_generator(self):
        return AIGenerator(
            api_key="test-key",
            model="test-model",
            base_url="https://example.test/chat/completions",
        )

    def make_tools(self):
        return [
            {
                "name": "search_course_content",
                "description": "Search course content",
                "input_schema": {
                    "type": "object",
                    "properties": {"query": {"type": "string"}},
                    "required": ["query"],
                },
            },
            {
                "name": "get_course_outline",
                "description": "Get course outline",
                "input_schema": {
                    "type": "object",
                    "properties": {"course_name": {"type": "string"}},
                    "required": ["course_name"],
                },
            },
        ]

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

        answer = generator.generate_response(
            "What is tool use?",
            tools=self.make_tools(),
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
        second_payload = generator._create_chat_completion.call_args_list[1].args[0]
        self.assertEqual(second_payload["tool_choice"], "auto")
        self.assertIn("tools", second_payload)
        self.assertEqual(second_payload["messages"][-1]["role"], "tool")
        self.assertEqual(second_payload["messages"][-1]["content"], "tool result")

    def test_generate_response_supports_two_sequential_tool_rounds(self):
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
                                "name": "get_course_outline",
                                "arguments": '{"course_name":"Course X"}',
                            },
                        }
                    ],
                },
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_2",
                            "type": "function",
                            "function": {
                                "name": "search_course_content",
                                "arguments": '{"query":"lesson 4 topic"}',
                            },
                        }
                    ],
                },
                {"role": "assistant", "content": "complete answer"},
            ]
        )
        manager = FakeToolManager(results=["outline result", "search result"])

        answer = generator.generate_response(
            "Search for a related course",
            tools=self.make_tools(),
            tool_manager=manager,
        )

        self.assertEqual(answer, "complete answer")
        self.assertEqual(generator._create_chat_completion.call_count, 3)
        first_payload = generator._create_chat_completion.call_args_list[0].args[0]
        second_payload = generator._create_chat_completion.call_args_list[1].args[0]
        final_payload = generator._create_chat_completion.call_args_list[2].args[0]
        self.assertIn("tools", first_payload)
        self.assertIn("tools", second_payload)
        self.assertNotIn("tools", final_payload)
        self.assertEqual(
            manager.calls,
            [
                ("get_course_outline", {"course_name": "Course X"}),
                ("search_course_content", {"query": "lesson 4 topic"}),
            ],
        )
        self.assertEqual(
            [message["role"] for message in final_payload["messages"]],
            ["system", "user", "assistant", "tool", "assistant", "tool"],
        )
        self.assertEqual(final_payload["messages"][3]["content"], "outline result")
        self.assertEqual(final_payload["messages"][5]["content"], "search result")

    def test_generate_response_returns_direct_answer_when_no_tool_call_needed(self):
        generator = self.make_generator()
        generator._create_chat_completion = Mock(
            return_value={"role": "assistant", "content": "direct answer"}
        )
        manager = FakeToolManager()

        answer = generator.generate_response(
            "What is retrieval?",
            tools=self.make_tools(),
            tool_manager=manager,
        )

        self.assertEqual(answer, "direct answer")
        self.assertEqual(generator._create_chat_completion.call_count, 1)
        self.assertEqual(manager.calls, [])
        first_payload = generator._create_chat_completion.call_args_list[0].args[0]
        self.assertIn("tools", first_payload)

    def test_generate_response_stops_gracefully_when_tool_execution_fails(self):
        generator = self.make_generator()
        generator._create_chat_completion = Mock(
            return_value={
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {
                            "name": "search_course_content",
                            "arguments": '{"query":"tool use"}',
                        },
                    }
                ],
            }
        )
        manager = FakeToolManager(fail_on_call=1)

        answer = generator.generate_response(
            "What is tool use?",
            tools=self.make_tools(),
            tool_manager=manager,
        )

        self.assertIn("couldn't complete the tool lookup", answer)
        self.assertEqual(generator._create_chat_completion.call_count, 1)
        self.assertEqual(
            manager.calls,
            [("search_course_content", {"query": "tool use"})],
        )

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
