""" MCP Server """
# import asyncio  # uncomment for MCP tools debugging
import json

from mcp.server.fastmcp import FastMCP
from smolagents import WebSearchTool

from utils import (OUTSIDE_KEYS, GmailService, GoogleCalendar, WeatherForecast,
                   convert_time_to_iso, get_curr_datetime_in_iso,
                   get_current_location, get_pollen_count,
                   get_traffic_conditions)

# Initialize FastMCP server
mcp = FastMCP("travel_conditions_check")


# Tools
@mcp.tool()
async def outdoor_location_examples() -> str:
    """
    Please use these keywords to identify if event is outside.
    If event name has one of these words it is likely to be outside,
    so you can advise to check weather and pollen count for this event.
    If event does not have these words it is likely to be inside,
    so you can advise to check if business is open or closed at the time of event.
    :return: list of words related to outdoor activities
    """
    return ", ".join(OUTSIDE_KEYS)


@mcp.tool()
async def get_weather_forecast(latitude: str, longitude: str) -> str:
    """Get weather forecast for a location by latitude and longitude
           If latitude and longitude values not known please use find_latitude_longitude_for_location
           or get_current_location tool
           :param latitude: Latitude of the location, e.g. 40.7128
           :param longitude: Longitude of the location e.g. -74.0060
           :return: forecast for the next 5 days (daytime and nighttime) in form of a string
           """
    weather_tool = WeatherForecast()
    return await weather_tool.get_weather_forecast(latitude, longitude)


@mcp.tool()
async def get_current_user_location(ip_address=None) -> str:
    """
    Returns location json. If no IP value is provided it will determine current location.
    IF IP is provided will return location data for a given IP.
    :param ip_address: provide if known
    :return: location json for a given IP address, example
            {'country_code': 'code_value', 'country_name': 'name_value',
            'city': 'city_value', 'postal': 'zip_code',
            'latitude': 'latitude_value', 'longitude': 'longitude_value', 'IPv4': 'ip_address', 'state': 'state_value'}
    """
    # ip_address = "63.116.61.152"  # this address is used for demo purposes
    return get_current_location(ip_address)


@mcp.tool()
async def use_web_search(query_message: str) -> str:
    """
    Use this tool to search the Web for answers, if other tools not helpful, and you do not know the answer
    :param query_message: query
    :return: search result from the Web
    """
    search_tool = WebSearchTool()
    return search_tool(query_message)


@mcp.tool()
async def get_current_datetime_in_iso(timezone_str: str) -> str:
    """
    Returns current date and time for Current time zone in ISO format
    :param timezone_str: Timezone string e.g.: "US/Pacific time" or "America/Austin"
    :return: example "2025-06-05T16:30:00-04:00"
    """
    return get_curr_datetime_in_iso(timezone_str)


@mcp.tool()
async def convert_local_time_to_iso(year: str | None, month: str, day: str, hour: str, minute: str | None,
                                    timezone_str: str) -> str:
    """
     Convert time components to local datetime string with timezone offset in RFC3339 format

     :param year: Year, current year is 2025
     :param month: Month can use names or corresponding numbers 1-12
     :param day: Day (1-31)
     :param hour: Hour in 24-hour format (0-23) or in 12 hours AM/PM format: "22" for 24-hour format,
            "12am" for 12-hour format
     :param minute: Minute (0-59), defaults to 0
     :param timezone_str: Timezone string e.g.: "US/Pacific time" or "America/Austin"

     :return:
         str: in RFC3339 format - ISO format datetime string with timezone offset (e.g.'2025-06-09T15:30:00-04:00')
     """
    return convert_time_to_iso(year, month, day, hour, minute, timezone_str)


@mcp.tool()
async def find_latitude_longitude_for_location(location_name: str) -> str:
    """
    Uses web search for find latitude and longitude for a provided location description
    Use to get specific place location for get_weather_forecast tool.
    :param location_name:  location name or description, e.g.: "New York", or "New York FL", or "New York Main street"
    :return: search result from the Web, there should be data which contains latitude and longitude,
    usually will be in the format of "40.7128,-74.0060" or "latitude 40.7128 and longitude -74.0060"
    or "40.7128 N,-74.0060 W" or something similar.
    We need only floating numbers "40.7128,-74.0060" to pass in get_weather_forecast tool.
    """
    search_tool = WebSearchTool()
    return search_tool(f"What are latitude and longitude for {location_name}")


@mcp.tool()
async def get_my_calendar_events(calendar_names=None, start_time=None, end_time=None) -> str:
    """
    Returns list of all events from the given calendars.
    If no start_time and end_time are provided, will return all events for today
    Note: when providing timestamp make sure it has correct time zone offset, e.g. New York tzm is "GMT -4" -> "-04:00"
    :param calendar_names: list of calendar names user wants to get events from,
    to get All Calendars pass empty list: list[]
    :param start_time: time as ISO timestamp e.g. "2025-06-05T16:30:00-04:00", if not provided,
    default value will be set to now
    :param end_time:time as ISO timestamp e.g. "2025-06-05T16:30:00-04:00", if not provided,
    default values will be set to the following midnight
    :return: list of calendar events with all required parameters
    event data structure example:  {"calendar_name": "primary", "calendar_id": "primary",
    "event_details": {"kind": "calendar#event", "etag": "\\"3493128575424894\\"",
    "id": "1qlglqpabc67g2k4ukip9_20250612T150000Z", "status": "confirmed",
    "htmlLink": "https://www.google.com/calendar/event?eid=MXFsZ2xxcHZjOGs0bGd0ZWRnMms0dWtpcwQG0",
    "created": "2025-06-04T19:11:32.000Z", "updated": "2025-06-04T19:11:32.712Z", "summary": "Team meeting",
    "location": "450 Lexington Ave, New York, NY 10017", "creator": {"email": "ttestltest230@gmail.com", "self": true},
    "organizer": {"email": "ttestltest230@gmail.com", "self": true},
    "start": {"dateTime": "2025-06-12T10:00:00-04:00", "timeZone": "America/New York"},
    "end": {"dateTime": "2025-06-12T11:00:00-04:00", "timeZone": "America/New York"},
    "recurringEventId": "1qlglqpvc8k4lgtebg2k4ukip9",
    "originalStartTime": {"dateTime": "2025-06-12T10:00:00-04:00", "timeZone": "America/New York”},
    "iCalUID": "1qlglabc67k4lgtedg2k4ukip9@google.com", "sequence": 0, "reminders": {"useDefault": true},
    "eventType": "default"},
    "start": "2025-06-12T10:00:00-04:00",
    "end": "2025-06-12T11:00:00-04:00",
    "location": "450 Lexington Ave, New York, NY 10017",
    "weather": "", "pollen": "", "is_business_closed": false, "traffic": ""}
    """
    #    my_events = read_json("test_data.json", None) # can use this if no access to calendar
    gmail_service = GmailService()
    calendar = GoogleCalendar(gmail_service.service)
    calendar_list = calendar.get_gmail_calendars(calendar_names)
    # get_gmail_calendars(gs, ["family"])
    # get_gmail_calendars(gs, ["gym"])
    # get_gmail_calendars(gs, ["gym", "main"])
    my_events = calendar.get_events_from_calendar(calendar_list, start_time, end_time)
    if my_events:
        result = "Found the next events: "
        for e in my_events:
            result += json.dumps(e.__dict__)
    else:
        result = "No events found."
    return result


@mcp.tool()
async def update_my_calendar_event(calendar_id: str, event_id: str, **kwargs) -> str:
    """
       Updates provided event with weather, pollen, traffic, and location data
       payload example1:{ calendar_id="abcalid", event_id="abcevid", weather ="snow",
                        traffic = "Allow 40-45 minutes", is_business_closed=False}
       payload example2:{ calendar_id="abcalid", event_id="abcevid",
                        pollen ="garass pollen moderate, tree pollen high",
                        location = "14 Marlow Ave, My City, NY"}
       :param calendar_id: "calendar_id", from event details provided by get_my_calendar_events()
       :param event_id: event "id", from event details provided by get_my_calendar_events()
       :param kwargs: supported keys weather, pollen, traffic, is_business_closed and location
             :return: confirmation that event was updated
       """
    gmail_service = GmailService()
    calendar = GoogleCalendar(gmail_service.service)
    result = calendar.update_event_properties(calendar_id, event_id, **kwargs)
    return result


@mcp.tool()
async def cleanup_my_event_summary(calendar_id: str, event_id: str) -> str:
    """
    Removes weather, pollen, traffic, and location icons from event summary
    :param calendar_id: "calendar_id", from event details provided by get_my_calendar_events()
    :param event_id: event "id", from event details provided by get_my_calendar_events()
    :return: confirmation that event was updated
    """
    gmail_service = GmailService()
    calendar = GoogleCalendar(gmail_service.service)
    result = calendar.cleanup_event_summary(calendar_id, event_id)
    return result


@mcp.tool()
async def cleanup_my_event_summary_by_key(calendar_id: str, event_id: str, **kwargs) -> str:
    """
    Removes weather, pollen, traffic, is_business_closed icons, and location from event
    :param calendar_id: "calendar_id", from event details provided by get_my_calendar_events()
    :param event_id: event "id", from event details provided by get_my_calendar_events()
    :param kwargs: supported keys weather, pollen, traffic, is_business_closed and location
    :return: confirmation that event was updated
    """
    gmail_service = GmailService()
    calendar = GoogleCalendar(gmail_service.service)
    result = calendar.cleanup_event_summary_icon(calendar_id, event_id, **kwargs)
    return result


@mcp.tool()
async def get_current_pollen_count(zipcode: str) -> str:
    """
    Visit pollen.com and similar pages for a specific zipcode to get the current pollen data for up to 5 days ahead
    Important data location: "forecast-chart" components
    - "https://www.pollen.com/forecast/current/pollen/" page:  "Top Allergens" section for Today and Tomorrow sections
    - "https://www.pollen.com/forecast/extended/pollen" page: "5 Day Allergy Forecast" with total daily count
    Please process this data to return pollen counts per day
    :param zipcode: location zipcode example, e.g. 07310
    :return: data from pollen.com or other pollen website
    """
    return get_pollen_count(zipcode)


@mcp.tool()
async def get_current_traffic_conditions(start_point_description: str, end_point_description: str) -> str:
    """
    Returns current traffic conditions between start_point_description and end_point_description
    :param start_point_description:  example 'Central Park, New York, NY'
    :param end_point_description: example 'Madame Tussauds New York, New York'
    :return:  traffic data is in the raw format, so you should parse it and summarise,
    Please pay attention to the "closed" or "may close" soon alerts, and display them to user
    working URL example: https://www.google.com/maps/dir/Central+Park+New+York/Madame+Tussauds
    """
    return get_traffic_conditions(start_point_description, end_point_description)


if __name__ == "__main__":
    """
    Initialize and run the server
    cmd usage: "python main_mcp_server.py"
    to debug tools use commands like:
    'print(asyncio.run(get_current_user_location()))'
    and comment out  'mcp.run(transport="stdio")'
    """
    mcp.run(transport="stdio")
