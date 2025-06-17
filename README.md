# Travel-Conditions-Checker-Example
This Agent can check for Weather alerts, Pollen count, 
and Traffic conditions based on your gmail calendar events. 
It also checks if business is open or closed,
and suggest to find an alternative for indoor/outdoor events if conditions are bad.

# Project setup
1. install python, download from https://www.python.org/downloads/
2. execute `pip install --upgrade pip`
3. cd into directory where you want to set up the project
4. `git clone https://github.com/ltest782/Travel-Conditions-Checker.git`
5. cd into project directory
6. execute `python3 -m venv .venv` (Note pycharm creates venv automatically)
7. execute `source .venv/bin/activate` (Note pycharm creates venv automatically)
8. optional command to check python version: `which python`
installs the requirements: `install -r requirements.txt`
10. In the project root directory add .env file with the next keys:
```
GOOGLE_CLIENT_ID=
GOOGLE_PROJECT_ID=
GOOGLE_SECRET=
ANTHROPIC_API_KEY=
```

# How to run
#### To run the command line Client with the provided MCP server, execute:  
`python main_mcp_client.py main_mcp_server.py`  
    Note: you can run Client with another MCP server, just provide correct path to the desired MCP server.

#### To run only MCP server:  
`python main_mcp_server.py`  

#### To use MCP server with AI Agent create a config file like this one for Claude Desktop:
-- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`  
-- Windows: `%APPDATA%\Claude\claude_desktop_config.json`  
```
{
    "mcpServers": {
        "travel_assistant": {
            "command": "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3",
            "args": [
                "/Users/YOU_USER_NAME_HERE/PycharmProjects/Travel-Conditions-Checker/main_mcp_server.py"
            ]
        }
    }
}
```

# Flow examples
#### User: check weather and pollen conditions for my tomorrow meetings between 3 and 6 pm
#### Agent actions: 
1. Get all meetings for all calendars for tomorrow between 3-6pm
2. If meeting has no Location:
  - Get user current location by IP
  - Clarify Location with User by printing out all scheduled events with approximate location
3. Check weather for events time
4. Check Pollen Alerts for that day
5. Print out summary for each event
6. Ask if user wants to update meeting summary, if YES:
  - Update meeting summary with corresponding icon for Rain/snow, severe weather alerts, and high pollen count

#### User: check traffic conditions for my tomorrow meetings from primary calendar
#### Agent actions: 
1. Get all meetings from primary calendar for tomorrow
2. If meeting has no Location:
  - Get user current location by IP
  - Clarify Location with User by printing out all scheduled events with approximate location
3. Check weather for events time
4. Check Pollen Alerts for that day
5. Check traffic conditions for each meeting
6. Check if business is open at meeting start time
7. Print out summary for each event
8. Ask if user wants to update meeting summary, if YES:
  - Update meeting summary with corresponding icon for Rain/snow, severe weather alerts, and high pollen count
  - Update meeting summary with traffic icon, and/or business closed icon




