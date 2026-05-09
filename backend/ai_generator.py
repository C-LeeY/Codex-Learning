import json
from typing import List, Optional, Dict, Any

import httpx


class AIGenerator:
    """Handles interactions with Zhipu AI's OpenAI-compatible chat API."""

    MAX_TOOL_ROUNDS = 2

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to course information tools.

Search Tool Usage:
- Use `search_course_content` only for questions about specific course content or detailed educational materials
- Use `get_course_outline` for outline-related questions, including course outline, syllabus, curriculum, course structure, modules, lesson list, or what lessons are in a course
- You may use tools sequentially when needed, up to two tool-calling rounds per user query
- Use the result of one tool call to decide whether a second tool call is necessary
- Synthesize tool results into accurate, fact-based responses
- If a tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without searching
- **Course-specific content questions**: Use `search_course_content` first, then answer
- **Course outline questions**: Use `get_course_outline` first, then answer with the course title, course link, and every lesson number and lesson title returned by the tool
- **No meta-commentary**:
 - Provide direct answers only - no reasoning process, search explanations, or question-type analysis
 - Do not mention "based on the search results" or "based on the tool results"


All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
For outline-related queries, do not summarize or omit lessons. Return the complete lesson list with each lesson number and title.
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str, base_url: str):
        if not api_key:
            raise ValueError("ZHIPU_API_KEY is not configured")

        self.model = model
        self.base_url = base_url
        self.client = httpx.Client(
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=60,
        )

        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800,
        }

    def generate_response(self, query: str,
                          conversation_history: Optional[str] = None,
                          tools: Optional[List] = None,
                          tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": query},
        ]

        if not tools or not tool_manager:
            response_message = self._create_chat_completion({
                **self.base_params,
                "messages": messages,
            })
            return response_message.get("content", "")

        openai_tools = self._to_openai_tools(tools)

        for _ in range(self.MAX_TOOL_ROUNDS):
            response_message = self._create_chat_completion({
                **self.base_params,
                "messages": messages,
                "tools": openai_tools,
                "tool_choice": "auto",
            })

            tool_calls = response_message.get("tool_calls") or []
            if not tool_calls:
                return response_message.get("content", "")

            messages.append(response_message)
            try:
                self._append_tool_results(messages, tool_calls, tool_manager)
            except Exception:
                return "I couldn't complete the tool lookup needed to answer this question. Please try again."

        final_message = self._create_chat_completion({
            **self.base_params,
            "messages": messages,
        })
        return final_message.get("content", "")

    def _append_tool_results(self, messages: List[Dict[str, Any]],
                             tool_calls: List[Dict[str, Any]], tool_manager) -> None:
        """Execute tool calls and append their results to the message history."""
        for tool_call in tool_calls:
            function = tool_call.get("function", {})
            tool_name = function.get("name")
            tool_args = self._parse_tool_arguments(function.get("arguments", "{}"))

            tool_result = tool_manager.execute_tool(tool_name, **tool_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "content": tool_result,
            })

    def _create_chat_completion(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        response = self.client.post(self.base_url, json=payload)
        response.raise_for_status()

        data = response.json()
        choices = data.get("choices", [])
        if not choices:
            raise ValueError("Zhipu AI response did not include any choices")

        return choices[0].get("message", {})

    def _parse_tool_arguments(self, arguments: Any) -> Dict[str, Any]:
        if isinstance(arguments, dict):
            return arguments

        try:
            parsed = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            return {}

        return parsed if isinstance(parsed, dict) else {}

    def _to_openai_tools(self, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        converted = []
        for tool in tools:
            converted.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {"type": "object"}),
                },
            })
        return converted
