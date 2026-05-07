import json
from typing import List, Optional, Dict, Any

import httpx


class AIGenerator:
    """Handles interactions with Zhipu AI's OpenAI-compatible chat API."""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to course information tools.

Search Tool Usage:
- Use `search_course_content` only for questions about specific course content or detailed educational materials
- Use `get_course_outline` for outline-related questions, including course outline, syllabus, curriculum, course structure, modules, lesson list, or what lessons are in a course
- **One tool call per query maximum**
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

        api_params = {
            **self.base_params,
            "messages": messages,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = self._to_openai_tools(tools)
            api_params["tool_choice"] = "auto"

        # Get response from Zhipu AI
        response_message = self._create_chat_completion(api_params)

        # Handle tool execution if needed
        if response_message.get("tool_calls") and tool_manager:
            return self._handle_tool_execution(response_message, api_params, tool_manager)

        # Return direct response
        return response_message.get("content", "")

    def _handle_tool_execution(self, initial_message: Dict[str, Any],
                               base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.

        Args:
            initial_message: The response containing tool call requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools

        Returns:
            Final response text after tool execution
        """
        messages = base_params["messages"].copy()
        messages.append(initial_message)

        # Execute all tool calls and collect results
        for tool_call in initial_message.get("tool_calls", []):
            function = tool_call.get("function", {})
            tool_name = function.get("name")
            tool_args = self._parse_tool_arguments(function.get("arguments", "{}"))

            tool_result = tool_manager.execute_tool(tool_name, **tool_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "content": tool_result,
            })

        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
        }

        # Get final response
        final_message = self._create_chat_completion(final_params)
        return final_message.get("content", "")

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
