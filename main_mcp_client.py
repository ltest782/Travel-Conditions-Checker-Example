"""MCP Client with Anthropic"""
import asyncio
import sys
from contextlib import AsyncExitStack
from enum import Enum
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

load_dotenv()  # load environment variables from .env


class MessageType(Enum):
    """ Chat Message types """
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL_USE = "tool_use"
    TOOL_RESULT = "tool_result"


class MCPClient:
    """
    MCP client with Anthropic
    """
    def __init__(self):
        # Initialize session and client objects
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.anthropic = Anthropic()
        self.message_history: list = []
        self.max_conversation_history = 1000
        self.stdio = None
        self.write = None

    def anthropic_call(self, messages, available_tools):
        """
        :param messages: list of messages
        :param available_tools: list of available MCP tools
        :return: result of message processing
        """
        system_message = ("You are a helpful travel assistant. You have the next abilities:"
                          "- You can get user's calendar events (get_my_calendar_events tool),"
                          "- You can use get_current_user_location to define user timezone and then "
                          "use get_current_datetime_in_iso or convert_local_time_to_iso tools to get proper datetime "
                          "values for start and end time to get events from calendar"
                          "- You can check Weather for a location (get_weather_forecast tool),"
                          "- You can get Pollen count for a zipcode (use get_current_pollen_count, "
                          "if no results use use_web_search tool),"
                          "- You can get traffic conditions (get_current_traffic_conditions tool) for events based on"
                          " the event time and location,"
                          "- You can check if business is closed or open at the event time using use_web_search tool,"
                          "If location is missing you can get it by checking current user location "
                          "via get_current_user_location tool, and asking user to confirm that location before"
                          " performing further operations."
                          "If existing or entered by user event location is not accurate e.g. has only city name "
                          "and no street address, you can try to use use_web_search tool to get an address and "
                          "location, do not forget to confirm with the user your findings."
                          "And you can use find_latitude_longitude_for_location tool to find latitude and longitude"
                          " values for the get_weather_forecast tool input based on a provided location description."
                          "You also can be proactive and advise user to search for another similar businesses nearby"
                          " if business is closed at the time of the scheduled event or event is outside and the"
                          " weather is bad at that time."
                          "Also if traffic is bad, it is nice to suggest to search for another route option or "
                          "change the activity."
                          "NOTE: current year is 2025, you can use get_current_datetime_in_iso tool to get exact "
                          "current time in ISO format with timezone offset."
                          "Once you found all requested information about upcoming events, you can update these e"
                          "vents in the calendar using update_my_calendar_event tool if user confirms, "
                          "also there is a cleanup_my_event_summary tool to fix the events in case of error."
                          "---"
                          "Discussion flow examples, and steps you should follow to solve the task:"
                          "Example 1:"
                          "User Task: check weather and pollen conditions for my tomorrow meetings between 3 and 6 pm"
                          "Agent actions:"
                          "1. Get user timezone and current time in ISO format, identify when is 'tomorrow 3pm "
                          "and tomorrow 6pm'"
                          "2. Get all meetings for all calendars for tomorrow between 3-6pm"
                          "3. If a meeting has no Location:"
                          "3.a. Get user current location"
                          "3.b. Confirm Location with User by printing out all scheduled events with known location, "
                          "and ask if user wants to replace 'No location' with the current location"
                          "3.c. If user confirms by replying yes/ok/confirm/'do it'/'go for it', then update meeting "
                          "location"
                          "4. Check weather for events time and location, if location unknown do nothing for that event"
                          "5. Check Pollen Alerts for that time and location, if location unknown do nothing for "
                          "that event"
                          "6. Print out summary for each event"
                          "7. Ask if user wants to update meeting summary, if YES:"
                          "7.a. Update meeting summary using update_my_calendar_event tool"
                          "8. Finish with some nice suggestion like 'Would you like more information about any of "
                          "these specific events?'"
                          "Example 2:"
                          "User Task: check traffic conditions for my Monday meetings from primary calendar"
                          "1. Get user timezone and current time in ISO format, identify when is 'Monday'"
                          "2. Get all meetings from primary calendar for Monday"
                          "3. If a meeting has no Location:"
                          "3.a. Get user current location"
                          "3.b. Confirm Location with User by printing out all scheduled events with known location, "
                          "and ask if user wants to replace 'No location' with the current location"
                          "3.c. If user confirms by replying yes/ok/confirm/'do it'/'go for it', then update meeting "
                          "location"
                          "4. Check weather for events time and location, if location unknown do nothing for that event"
                          "5. Check Pollen Alerts for that time and location, if location unknown do nothing for "
                          "that event"
                          "6. Check traffic conditions for each meeting:"
                          "6.a. Sort meetings by start time (they already should be sorted by get_my_calendar_events, "
                          "but just in case make sure they are properly sorted)"
                          "6.b. Check traffic between each meeting pair: if meetings have same location, then no need "
                          "to check traffic. If there is only one meeting, check traffic from the current user location"
                          " to the meeting location if they are different."
                          "7. Check if business is open at arrival time."
                          "8. Print out summary for each event."
                          "9. Ask if user wants to update meeting summary, if YES:"
                          "7.a. Update meeting summary using update_my_calendar_event tool"
                          "8. Finish with some nice suggestion like 'Would you like more information about any of "
                          "these specific events or travel conditions?'"
                          "NOTE: check all conditions means: check traffic, check weather, check pollen, check if "
                          "business open or closed"
                          "---"
                          "Rules to follow when calling tools:"
                          "1. Always use the right type arguments for the tools."
                          "2. Perform proper datetime conversion before passing the datetime arguments."
                          "3. Store all search results and tools outputs to reuse them for the following questions. "
                          "Example if you got weather for New York for the next 5 days, and user asks you to check"
                          " weather for day 1, then day 3, then day 4 -> you can use already retrieved data "
                          "without searching. If user asks about the weather on the day 6 you will have to perform"
                          " a new search due to your current data has only days 1-5."
                          "4. When receiving events you need to remember event id and calendar_id, because this info"
                          " is required to update the events."
                          )
        try:
            result = self.anthropic.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                messages=messages,
                tools=available_tools,
                system=system_message
            )
            return result
        except Exception as e:
            return {f"An error occurred while calling Anthropic model: {e}"}

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        :param server_script_path: Path to the server script (.py or .js)
        """
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env=None
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        # List available tools
        response = await self.session.list_tools()
        tools = response.tools
        print("\nConnected to MCP server with the next tools:", [tool.name for tool in tools])

    async def process_anthropic_call(self, initial_message, available_tools) -> list[str]:
        """
        Processing the result of Anthropic LLM call, which can be a Text or a Tool or both
        :param initial_message: origin user message received in the chat
        :param available_tools: list of MCP server tools
        :return: Final answer with processing history
        """
        if initial_message:
            self.message_history.append(initial_message)
        # Initial Claude API call
        ai_response = self.anthropic_call(self.message_history, available_tools)
        if "error" in ai_response:
            return [f"An error occurred: {ai_response["error"]}"]

        # Process response and handle tool calls
        final_text = []
        for content in ai_response.content:
            if content.type == "text":
                final_text.append(f"\n{content.text}")
                self.message_history.append({
                    "role": MessageType.ASSISTANT.value,
                    "content": content.text
                })
            elif content.type == "tool_use":
                tool_name = content.name
                tool_args = content.input
                tool_id = content.id

                # Execute tool call
                print(f"tool_usage:{content}")
                final_text.append(f"\nCalling tool {tool_name}:{tool_id} with args {tool_args}...")
                tool_result = await self.session.call_tool(tool_name, tool_args)  # when read_timeout_seconds=60 -> bug

                message = {
                    "role": MessageType.ASSISTANT.value,
                    "content": [{"type": MessageType.TOOL_USE.value,
                                 "id": tool_id,
                                 "name": tool_name,
                                 "input": tool_args}]
                }
                self.message_history.append(message)
                try:
                    if hasattr(tool_result, "content"):
                        for tool_content in tool_result.content:
                            if tool_content.type == "text":
                                message = {
                                    "role": MessageType.USER.value,
                                    "content": [{
                                        "type": MessageType.TOOL_RESULT.value,
                                        "tool_use_id": tool_id,
                                        "content": tool_content.text,
                                        "is_error": tool_result.isError
                                    }],
                                }
                                # Get the next response from Claude, after processing tool results
                                ai_with_tool_response = await self.process_anthropic_call(message, available_tools)
                                final_text.append("\n".join(ai_with_tool_response))
                            else:
                                return[f"Unexpected tool content type: {tool_content.type}, expected str"]

                    else:
                        message = {
                            "role": MessageType.USER.value,
                            "content": [{
                                "type": MessageType.TOOL_RESULT.value,
                                "tool_use_id": tool_id,
                                "content": f"{tool_result.model_dump_json()}",
                                "is_error": tool_result.isError
                            }],
                        }
                        # Get the next response from Claude
                        ai_with_tool_response = await self.process_anthropic_call(message, available_tools)
                        final_text.append("\n".join(ai_with_tool_response))
                except Exception as e:
                    final_text.append(f"\n Error calling tool '{tool_name}': {e}")
        return final_text

    async def process_query(self, query: str) -> str:
        """
        Process a query using LLM and available MCP tools
        :param query: initial user query
        :return: final answer
        """
        message = {
            "role": MessageType.USER.value,
            "content": query
        }
        response = await self.session.list_tools()
        available_tools = [{
            "name": tool.name,
            "description": tool.description,
            "input_schema": tool.inputSchema
        } for tool in response.tools]

        # Initial API call to AI
        ai_response = await self.process_anthropic_call(message, available_tools)
        return "\nANSWER:".join(ai_response)

    async def chat_loop(self):
        """Run an interactive chat loop until exit/quit request"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit/exit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()
                if query.lower() in ["quit", "exit"]:
                    break
                # process the query
                response = await self.process_query(query)
                # output the result
                print("\n" + response)
                # trim the message history to prevent overflow
                if len(self.message_history) > self.max_conversation_history:
                    self.message_history = self.message_history[-self.max_conversation_history:]

            except Exception as e:
                print(f"\nError: {str(e)}")
                print(f"Current message history: {self.message_history}")
                print("Cleaning message history...")
                self.message_history = []

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    """
    Initialize and run the client
    """
    if len(sys.argv) < 2:
        print("Usage: python main_mcp_client.py main_mcp_server.py")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    asyncio.run(main())
