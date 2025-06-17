""" Collection of Tool used by MCP server and client """
import datetime
import json
import os
import os.path
import re
from enum import Enum
from typing import Any
from urllib import parse, request

import httpx
import pytz
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from lxml import etree
from smolagents import WebSearchTool

load_dotenv()

OUTSIDE_KEYS = [
    "exercise", "jogg", "jogging", "yoga", "run", "running", "stretch", "stretching", "walk", "walking", "beach",
    "soccer", "sport", "football", "volleyball", "dance", "skiing", "sky diving", "surfing", "trail", "bike",
    "basketball", "baseball", "lacrosse", "park", "forest", "woods", "picnic", "lake", "lawn", "concert", "pool",
    "swim", "swimming", "sail", "sailing", "cycling", "kayaking", "rafting", "rock climbing", "fishing", "skating",
    "biking", "bicycling", "recreation", "river", "sea", "ocean", "stroll", "pond", "preserve", "nature", "woods",
    "camping", "mountaineering", "canoeing", "caving", "croquet", "cricket", "golf", "hockey", "paintball",
    "pickleball", "tennis", "rodeo", "rugby", "festival", "skateboarding", "sledding", "snowboarding", "snow tubing",
    "softball", "triathlon", "marathon", "carnaval", "parade", "show", "farmers market", "flea market", "sunday market"]
GEOLOCATION_URL = "https://geolocation-db.com/json"
NO_LOCATION_STR = "No location"
POLLEN_URL1 = "https://www.pollen.com/forecast/current/pollen"
POLLEN_URL2 = "https://www.pollen.com/forecast/extended/pollen"
GOOGLE_MAPS_URL = "https://www.google.com/maps/dir"


class TCCIcons(Enum):
    """ Icons to add to Calendar events to represent environment conditions"""
    RAIN = ("☂️", "rain")
    SNOW = ("❄️", "snow")
    BAD_TRAFFIC = ("🚗", "traffic")
    POLLEN = ("🤧", "pollen")  # or "🦠" ?
    CLOSED = ("⛔", "is_business_closed")
    ALERT = ("⚠️", "alert")

    def __init__(self, icon, description):
        self.icon = icon
        self.description = description


class WebPageDOM:
    """ Class to get WebPage DOM structure """
    def __init__(self, url):
        """
        Initialize the WebPageDOM class.
        :param url (str): The URL of the webpage to read.
        """
        self.url = url
        self.dom, self.soup = self._get_dom()

    def _get_dom(self):
        """
        Get the DOM structure of the webpage.
        :return: A BeautifulSoup object representing the DOM structure.
        """
        try:
            response = requests.get(self.url, timeout=60)
            response.raise_for_status()  # Raise an exception for HTTP errors
            soup = BeautifulSoup(response.text, 'html.parser')
            dom = etree.HTML(str(soup))
            return dom, soup
        except requests.exceptions.RequestException as err:
            print(f"Error getting dom object for the '{self.url}' webpage: {err}")
            return None, None

    def print_dom(self):
        """
        Print the DOM structure of the webpage.
        """
        return f"{self.soup.prettify()}"

    def find_elements(self, xpath: str):
        """
        Finds multiple elements in the DOM structure.

        :param xpath: xpath to find elements
        :return: A list of found elements.
        """
        return self.dom.xpath(xpath)


def read_json(file_path, key_name):
    """
    Reads data from a JSON file and returns the value associated with a given key.

    :param file_path: The path to the JSON file.
    :param key_name: The key to search for in the JSON data.
    :return: The value associated with the key, or None if the key is not found.
    If no key_name provided: returns entire file content
    """
    try:
        with open(file_path, "r") as file:
            data = json.load(file)
            if key_name:
                return data.get(key_name)
            return data
    except FileNotFoundError:
        print(f"Error: File not found: '{file_path}'.")
        return None
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON format in '{file_path}'.")
        return None


class WeatherForecast:
    """ Class to get Weather forecast"""
    WEATHER_URL = "https://api.weather.gov"
    WEATHER_AGENT = "weather-app/1.0"

    async def get_weather_api(self, url: str) -> dict[str, Any] | None:
        """
        Make a request to the Weather.gov API with proper error handling.
        :param url:
        :return: weather data in json format
        """
        headers = {
            "User-Agent": self.WEATHER_AGENT,
            "Accept": "application/geo+json"
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, timeout=30.0)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                print(f"An error occurred while attempting to get weather data: {e}")

    def format_weather_alert_data(self, alert_data: dict) -> str:
        """Format alert dict into a readable string.
        :param alert_data: raw alert data
        :return: formatted str with readable data
        """
        props = alert_data["properties"]
        return f"""
        Event: {props.get("event", "Unknown")}
        Area: {props.get("areaDesc", "Unknown")}
        Severity: {props.get("severity", "Unknown")}
        Description: {props.get("description", "No description available")}
        Instructions: {props.get("instruction", "No specific instructions provided")}
        """

    def format_forecast_period_data(self, period: dict) -> str:
        """
        Format weather period dict into a readable string.
        :param period: raw weather period data
        :return: formatted str with readable data
        """
        return f"""
        {period.get("name", "Unknown")}:
        Temperature: {period.get("temperature", "Unknown")}°{period.get("temperatureUnit", "Unknown")}
        Precipitation: {period.get("probabilityOfPrecipitation", {}).get("value", "Unknown")} %
        Forecast: {period.get("detailedForecast", "Unknown")}
        """

    async def get_weather_alerts(self, zone_id: str) -> str:
        """Get weather alerts for a forecast zone.
        :param zone_id: forecast zone code from get_points API
        :return: weather alerts if any
        """
        result = ""
        url = f"{self.WEATHER_URL}/alerts/active/zone/{zone_id}"
        data = await self.get_weather_api(url)

        if not data or "features" not in data:
            return f"Unable to get alerts for {url}."

        if not data.get("features"):
            return "No active alerts for this zone."

        alerts = [self.format_weather_alert_data(feature) for feature in data["features"]]
        if alerts:
            return f"⚠️ Weather Alerts: {"---".join(alerts)}"

        return result

    async def get_weather_forecast(self, latitude_str: str, longitude_str: str) -> str:
        """Get weather forecast for a location by latitude and longitude
        If latitude and longitude values not known please use find_latitude_longitude_for_location
        or get_current_location tool

        :param latitude_str: Latitude of the location, e.g. 40.7128
        :param longitude_str: Longitude of the location e.g. -74.0060
        :return: forecast for the next 5 days (daytime and nighttime) in form of a string
        """
        try:
            latitude = f"{float(latitude_str):.4f}"
            longitude = f"{float(longitude_str):.4f}"
            if not (-90 < float(latitude) < 90):
                return f"Got wrong latitude value: {latitude}. Value should be in a range of -90 - 90."

            if not (-180 < float(longitude) < 180):
                return f"Got wrong latitude value: {longitude}. Value should be in a range of -180 - 180."

            # First get the forecast grid endpoint
            points_url = f"{self.WEATHER_URL}/points/{latitude},{longitude}"
            points_data = await self.get_weather_api(points_url)

            if not points_data:
                return "Unable to fetch forecast data for this location."

            # get alerts if any:
            forecast_zone_url = points_data.get("properties", {}).get("forecastZone", "")
            weather_alerts = ""
            if forecast_zone_url:
                zone_id = forecast_zone_url.split("/")[-1]
                weather_alerts = await self.get_weather_alerts(zone_id)

            # Get the forecast URL from the points response
            forecast_url = points_data.get("properties", {}).get("forecast")
            forecast_data = await self.get_weather_api(forecast_url)

            if not forecast_data:
                return f"Unable to get detailed forecast from {forecast_url}."

            # Format the periods into a readable forecast
            periods = forecast_data.get("properties", {}).get("periods")
            forecasts = []
            for period in periods:
                forecast = self.format_forecast_period_data(period)
                forecasts.append(forecast)
            forecasts_str = "---".join(forecasts)
            return f"{weather_alerts}\n Forecast: {forecasts_str}"
        except Exception as e:
            return f"An error occurred while attempting to get weather: {e}"


class CalendarEvent:
    """ Class to store Calendar Event data """

    def __init__(self, calendar_name: str, calendar_id: str, event_details: dict[Any, Any], start: str, end: str,
                 location: str, weather: str = "", pollen: str = "", is_business_closed: bool = False,
                 traffic: str = ""):
        self.calendar_name = calendar_name
        self.calendar_id = calendar_id
        self.event_details = event_details
        self.start = start
        self.end = end
        self.location = location
        self.weather = weather
        self.pollen = pollen
        self.is_business_closed = is_business_closed
        self.traffic = traffic


class Calendar:
    """Class to store Calendar data"""

    def __init__(self, calendar_id: str, name: str, data: dict[Any, Any]):
        self.calendar_id = calendar_id
        self.name = name
        self.data = data


class GmailService:
    """
    Connects to the gmail service as a desktop app,
    because this tool is designed to be a personal assistant due to data privacy
    """
    _instance = None
    _initialized = False
    GOOGLE_CLIENT_ID = os.environ['GOOGLE_CLIENT_ID']
    GOOGLE_PROJECT_ID = os.environ['GOOGLE_PROJECT_ID']
    GOOGLE_SECRET = os.environ['GOOGLE_SECRET']
    SCOPES = ['https://www.googleapis.com/auth/calendar.events.owned',
              'https://www.googleapis.com/auth/calendar.readonly']
    CLIENT_CONFIG = {
        "web": {
            "client_id": GOOGLE_CLIENT_ID,
            "project_id": GOOGLE_PROJECT_ID,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_secret": GOOGLE_SECRET,
            "redirect_uris": [
                "http://localhost:8080"
            ],
            "javascript_origins": [
                "http://localhost:8080"
            ]
        }
    }

    def __new__(cls):
        """Override __new__ to control instance creation"""
        if cls._instance is None:
            cls._instance = super(GmailService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize only once"""
        if not GmailService._initialized:
            # Initialize your data here
            self.service = self._get_gmail_service()
            GmailService._initialized = True

    def _get_gmail_service(self):
        """
        Returns gmail service if connection is successful
        Requires credentials.json in the main directory
        :return: gmail service
        """
        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", self.SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_config(self.CLIENT_CONFIG, self.SCOPES)
                # flow.redirect_uri = 'https://localhost:8080/oauth2callback'
                creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
        try:
            service = build("calendar", "v3", credentials=creds)  # , cache=MemoryCache()
            return service
        except Exception as e:
            print(f"An error occurred while attempting to connect to gmail service: {e}")
            return None


class GoogleCalendar:
    """ Class to work with Google calendar"""
    MAX_EVENTS_FROM_CALENDAR = 10
    PRIMARY_CALENDAR_ID = "primary"
    NO_LOCATION_STR = "No location"

    def __init__(self, google_service: GmailService):
        self.gmail_service = google_service

    def set_max_number_of_events(self, max_number):
        """
        Set max number of events to be retrieved from a Calendar
        :param max_number: int ,e.g. default value is 10
        """
        GoogleCalendar.MAX_EVENTS_FROM_CALENDAR = int(max_number)

    def add_to_calendar_list(self, calendar, calendar_list):
        """
        Adds a Calendar instance to an available calendar list
        :param calendar: current calendar json
        :param calendar_list: calendar list
        :return:
        """
        calendar_data = Calendar(calendar_id=calendar["id"], name=calendar["summary"], data=calendar)
        calendar_list.append(calendar_data)

    def get_gmail_calendars(self, calendar_names) -> list[str] | None:
        """
        Get list of all accessible calendars, and parse it to get requested calendar ids
        :param calendar_names: list of calendar names
        :return: list of available calendar ids
        """
        if not calendar_names:
            calendar_names = []
        elif not isinstance(calendar_names, list):
            calendar_names = [calendar_names]
        calendar_list = []
        lowercase_calendar_names = []
        if calendar_names:
            lowercase_calendar_names = [item.lower() for item in calendar_names]
        try:
            results = self.gmail_service.calendarList().list().execute()
            for c in results["items"]:
                if c.get("primary", False):
                    c["id"] = self.PRIMARY_CALENDAR_ID
                    c["summary"] = self.PRIMARY_CALENDAR_ID
                if not calendar_names:
                    # add calendar to the list
                    self.add_to_calendar_list(c, calendar_list)
                else:
                    possible_primary_calendar_names = ["main", "default"]
                    for cn in lowercase_calendar_names:
                        if cn in c["summary"].lower():
                            # add calendar to the list
                            self.add_to_calendar_list(c, calendar_list)
                        elif cn in possible_primary_calendar_names and c["id"] == self.PRIMARY_CALENDAR_ID:
                            # add calendar to the list
                            self.add_to_calendar_list(c, calendar_list)
            return calendar_list
        except Exception as e:
            print(f"An error occurred while attempting to get gmail calendars: {e}")
            return calendar_list

    def get_events_from_calendar(self, calendar_list, start_time, end_time):
        """
        Returns list of all events from the given calendars.
        If no start_time and end_time are provided, will return all events for today
        :param calendar_list: list of accessible calendar ids
        :param start_time: time as ISO timestamp, if not provided, default value will be set to now
        :param end_time:time as ISO timestamp, if not provided, default values will be set to midnight
        :return: list of calendar events: list[CalendarEvent]
        """
        event_list = []
        try:
            if not start_time:
                start_time = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
            if not end_time:
                start_dt = datetime.datetime.fromisoformat(str(start_time))
                midnight_dt = start_dt.replace(hour=0, minute=0, second=0, microsecond=0) + datetime.timedelta(days=1)
                end_time = midnight_dt.isoformat()
            # print(f"Got time: {start_time} - {end_time}.")
            for c in calendar_list:
                # Call the Calendar API
                print(f"Getting the upcoming {self.MAX_EVENTS_FROM_CALENDAR} events...")
                events_result = (
                    self.gmail_service.events().list(calendarId=c.calendar_id, timeMin=start_time, timeMax=end_time,
                                                     maxResults=self.MAX_EVENTS_FROM_CALENDAR, singleEvents=True,
                                                     orderBy="startTime").execute())

                events = events_result.get("items", [])
                if not events:
                    print(f"No upcoming events found for '{c.name}' calendar.")
                # Prints the start and name of the upcoming events
                for event in events:
                    start = event["start"].get("dateTime", event["start"].get("date"))
                    end = event["end"].get("dateTime", event["end"].get("date"))
                    if event.get("location"):
                        location = event.get("location")
                    else:
                        location = self.NO_LOCATION_STR
                        if event.get("workingLocationProperties"):
                            if event["workingLocationProperties"].get("homeOffice"):
                                location = event["workingLocationProperties"]["homeOffice"]
                            elif event["workingLocationProperties"].get("officeLocation"):
                                working_location = self.collect_dict_values(event["workingLocationProperties"],
                                                                            "officeLocation")
                                if working_location:
                                    location = working_location
                            elif event["workingLocationProperties"].get("customLocation"):
                                custom_location = self.collect_dict_values(event["workingLocationProperties"],
                                                                           "customLocation")
                                if custom_location:
                                    location = custom_location
                    event_obj = CalendarEvent(calendar_name=c.name, calendar_id=c.calendar_id, event_details=event,
                                              start=start, end=end, location=location)
                    event_list.append(event_obj)
                    print(f"{start}-{end}: '{event["summary"]}', {location}.")
            return event_list
        except Exception as e:
            print(f"An error occurred while attempting to get calendar events: {e}")
            return event_list

    def collect_dict_values(self, data: dict, key: str) -> str:
        """
        Internal method to collect location data from event properties
        :param data: event data
        :param key: location related key
        :return: provided key value if any
        """
        result = ""
        for _, value in data[key]:
            if value:
                result += f"{value} "
        return result

    def update_event_properties(self, calendar_id: str, event_id: str, **kwargs) -> str:
        """
        Updates Gmail calendar event summary with icons representing external conditions
        :param calendar_id: Calendar id from event properties
        :param event_id: event id
        :param kwargs: one of [location, weather, pollen, traffic, is_business_closed]
        :return: success/error message
        """
        event_details = {"calendar_id": calendar_id, "event_id": event_id}
        try:
            event_details = self.gmail_service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            # fixing AI glitch
            for key, value in kwargs.items():
                if key == "kwargs":
                    kwargs = value
                    break
            # regular flow
            for key, value in kwargs.items():
                event_summary = event_details["summary"]
                if key == "location":
                    event_details[key] = value
                elif key == TCCIcons.CLOSED.description and bool(value):
                    event_summary = self.update_summary_value(TCCIcons.CLOSED.icon, event_summary)
                elif key == TCCIcons.BAD_TRAFFIC.description:
                    if any(x in value.lower() for x in ["extra", "extra time", "high", "heavy", "hour"]):
                        event_summary = self.update_summary_value(TCCIcons.BAD_TRAFFIC.icon, event_summary)
                elif key == TCCIcons.POLLEN.description:
                    if any(x in value.lower() for x in ["moderate", "medium", "high"]):
                        event_summary = self.update_summary_value(TCCIcons.POLLEN.icon, event_summary)
                elif key == "weather":
                    if TCCIcons.SNOW.description in value.lower():
                        event_summary = self.update_summary_value(TCCIcons.SNOW.icon, event_summary)
                    elif any(x in value.lower() for x in ["rain", "thunder", "shower"]):
                        event_summary = self.update_summary_value(TCCIcons.RAIN.icon, event_summary)
                    elif any(x in value.lower() for x in ["alert", "warning", "tornado", "storm"]):
                        event_summary = self.update_summary_value(TCCIcons.ALERT.icon, event_summary)

                event_details["summary"] = event_summary
            self.gmail_service.events().update(calendarId=calendar_id, eventId=event_id, body=event_details).execute()
        except Exception as e:
            return f"An error occurred while attempting to update event '{event_details.get("summary")}' : {e}"
        return f"'{event_details.get("summary")}' event was successfully updated"

    def update_summary_value(self, icon, event_summary, clear=False):
        """
        Adds or removes the icon from the event summary
        :param icon: Icon to add/remove
        :param event_summary: Calendar event summary
        :param clear: True to remove, False to add
        """
        if icon not in event_summary and not clear:
            return f"{icon} {event_summary}"
        if icon in event_summary and clear:
            return event_summary.replace(f"{icon} " , "")
        return event_summary


    def cleanup_event_summary_icon(self, calendar_id: str, event_id: str, **kwargs):

        """
        Updates Gmail calendar event summary with icons representing external conditions
        :param calendar_id: Calendar id from event properties
        :param event_id: event id
        :return: success/error message
        """
        event_details = {"calendar_id": calendar_id, "event_id": event_id}
        try:
            event_details = self.gmail_service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            event_summary = event_details["summary"]
            # fixing AI glitch
            for key, value in kwargs.items():
                if key == "kwargs":
                    kwargs = value
                    break
            # regular flow
            for key, _ in kwargs.items():
                if key == "location":
                    event_details[key] = ""
                elif key == TCCIcons.CLOSED.description:
                    event_summary = self.update_summary_value(TCCIcons.CLOSED.icon, event_summary, True)
                elif key == TCCIcons.BAD_TRAFFIC.description:
                    event_summary = self.update_summary_value(TCCIcons.BAD_TRAFFIC.icon, event_summary, True)
                elif key == TCCIcons.POLLEN.description:
                    event_summary = self.update_summary_value(TCCIcons.POLLEN.icon, event_summary, True)
                elif key == "weather":
                    weather_list = [TCCIcons.SNOW.icon, TCCIcons.RAIN.icon, TCCIcons.ALERT.icon]
                    for x in weather_list:
                        if x in event_summary:
                            event_summary = self.update_summary_value(x, event_summary, True)
            event_details["summary"] = event_summary
            self.gmail_service.events().update(calendarId=calendar_id, eventId=event_id, body=event_details).execute()
        except Exception as e:
            return f"An error occurred while attempting to update event '{event_details.get("summary")}' : {e}"
        return f"'{event_details.get("summary")}' event was successfully updated"


    def cleanup_event_summary(self, calendar_id: str, event_id: str) -> str:
        """
        Updates Gmail calendar event summary with icons representing external conditions
        :param calendar_id: Calendar id from event properties
        :param event_id: event id
        :return: success/error message
        """
        event_details = {"calendar_id": calendar_id, "event_id": event_id}
        try:
            event_details = self.gmail_service.events().get(calendarId=calendar_id, eventId=event_id).execute()
            icons = [i.icon for i in TCCIcons]
            for x in icons:
                if x in event_details["summary"]:
                    event_details["summary"] = event_details["summary"].replace(f"{x} ", "")
            self.gmail_service.events().update(calendarId=calendar_id, eventId=event_id, body=event_details).execute()
        except Exception as e:
            return f"An error occurred while attempting to update event '{event_details.get("summary")}' : {e}"
        return f"'{event_details.get("summary")}' event was successfully updated"


def get_current_location(ip_address=None) -> str:
    """
    Returns location json. If no IP value is provided it will determine current location.
    IF IP is provided will return location data for a given IP.
    :param ip_address:
    :return: location json for a given IP address, example
            {'country_code': 'code_value', 'country_name': 'name_value',
            'city': 'city_value', 'postal': 'zip_code',
            'latitude': 'latitude_value', 'longitude': 'longitude_value', 'IPv4': 'ip_address', 'state': 'state_value'}
    """
    if ip_address:
        geo_url = f"{GEOLOCATION_URL}/{ip_address}"
    else:
        geo_url = GEOLOCATION_URL
    try:
        with request.urlopen(geo_url) as url:
            data = json.loads(url.read().decode())
        return f"{data}"
    except Exception as e:
        return f"An error occurred while attempting to get location: {e}"


def get_curr_datetime_in_iso(timezone_str: str) -> str:
    """
    Returns current date and time for provided time zone in ISO format
    :param timezone_str: Timezone string e.g.: "US/Pacific time" or "America/Austin"
    :return: example "2025-06-05T16:30:00-04:00"
    """
    # Create timezone object
    local_tz = pytz.timezone(timezone_str)
    now = datetime.datetime.now(tz=local_tz)
    return now.strftime('%Y-%m-%dT%H:%M:%S%z')


def convert_12_to_24_hour(hour_value: str) -> str:
    """
    Convert 12-hour format to 24-hour format.

    :param hour_value: string representing hour e.g. "3PM" or "2 AM",
        if only number is provided, we assume it is in 24-hour format already, e.g. "5", "17"
    :return: Hour in 24-hour format (0-23)
    """
    hour_24 = hour_value.strip().lower()
    if bool(re.match(r'^(?:[0-1]?[0-9]|2[0-3])$', hour_24)):
        return hour_24

    if bool(re.match(r'(?:0?[1-9]|1[0-2])\s*(?:[ap]m)', hour_24)):
        for am_pm in ["am", "pm"]:
            if am_pm in hour_24:
                hour_split = hour_24.split(am_pm)[0].strip()
                hour_12 = int(hour_split)
                if am_pm == "am":
                    return "0" if hour_12 == 12 else hour_split
                # PM
                return hour_split if hour_12 == 12 else (hour_12 + 12)

    return f"Was not able to parse this hour value: {hour_value}"


def convert_month_to_number(month_value: str) -> str:
    """
        Convert month name to number

        :param month_value: Month name (full or abbreviated)
        :return: Month number (1-12)
        """
    try:
        # Handle both full and abbreviated month names
        # Convert to proper case for parsing
        month_name = str(month_value).strip().capitalize()
        if bool(re.match(r'(?:0[1-9]|1[0-2]|[1-9])', month_name)):
            return month_name
        # Try full month name first
        try:
            month_obj = datetime.datetime.strptime(month_name, '%B')
            return str(month_obj.month)
        except ValueError:
            # Try abbreviated month name
            month_obj = datetime.datetime.strptime(month_name, '%b')
            return str(month_obj.month)

    except ValueError:
        return f"Was not able to parse this month value: {month_value}"


def convert_time_to_iso(year: str | None, month: str, day: str, hour: str, minute: str | None,
                        timezone_str: str) -> str:
    """
     Convert time components to local datetime string with timezone offset in RFC3339 format

     :param  year: Year, current year is 2025
     :param  month: Month can use names or corresponding numbers 1-12
     :param day: Day (1-31)
     :param hour: Hour in 24-hour format (0-23) or in 12 hours AM/PM format: "22" for 24-hour format,
             "12am" for 12-hour format
     :param minute: Minute (0-59), defaults to 0
     :param timezone_str: Timezone string e.g.: "US/Pacific time" or "America/Austin"

     :return: in RFC3339 format - ISO format datetime string with timezone offset (e.g.'2025-06-09T15:30:00-04:00')
     """
    try:
        if not year:
            year = 2025
        if "m" in hour.lower():
            hour = convert_12_to_24_hour(hour)
        if not minute:
            minute = 0
        month = convert_month_to_number(month)
        # Create timezone object
        local_tz = pytz.timezone(timezone_str)
        # Create datetime object in local timezone
        local_dt = datetime.datetime(int(year), int(month), int(day), int(hour), int(minute), 0)
        local_dt = local_tz.localize(local_dt)

        # Return in ISO format with timezone offset
        return local_dt.strftime('%Y-%m-%dT%H:%M:%S%z')

    except Exception as e:
        return f"Was not able to convert given time to ISO format: {str(e)}"


def get_pollen_count(zipcode: str) -> str:
    """
    Visit pollen.com and similar pages for a specific zipcode to get the current pollen data for up to 5 days ahead
    Important data location: "forecast-chart" components
    - "https://www.pollen.com/forecast/current/pollen/" page:  "Top Allergens" section for Today and Tomorrow sections
    - "https://www.pollen.com/forecast/extended/pollen" page: "5 Day Allergy Forecast" with total daily count
    Please process this data to return pollen counts per day
    :param zipcode: location zipcode example, e.g. 07310
    :return: data from pollen.com or other pollen website
    """
    try:
        if not bool(re.match(r'^\d{5}$', zipcode.strip())):
            return f"zipcode should be 5 digits long e.g.92003, got {zipcode}."
        pollen_page = WebSearchTool()
        page1_data = pollen_page(f"{POLLEN_URL1}/{zipcode}")
        page2_data = pollen_page(f"{POLLEN_URL2}/{zipcode}")
        return f"{page1_data}/n{page2_data}"
    except Exception as e:
        return f"An error occurred while attempting to get location: {e}"


def get_traffic_conditions(start_point_description: str, end_point_description: str) -> str:
    """
    Returns current traffic conditions between start_point_description and end_point_description
    :param start_point_description:  example 'New Trier High School, Winnetka, IL'
    :param end_point_description: example 'Shedd Aquarium, Chicago, IL'
    :return:  traffic data is in the raw format, so you should parse it and summarise,
    Please pay attention to the "closed" or "may close" soon alerts, and display them to user
    working URL example: https://www.google.com/maps/dir/Chicago+Botanic+Garden/Navy+Pier+Wheel
    """
    final_data = ""
    try:
        start_point = parse.quote_plus(start_point_description)
        end_point = parse.quote_plus(end_point_description)
        url = f"{GOOGLE_MAPS_URL}/{start_point}/{end_point}"
        gmaps_dom = WebPageDOM(url)
        data_to_parse = gmaps_dom.print_dom()
        start_char = '"directions'
        body_data = data_to_parse.split(start_char)
        if len(body_data) > 1:
            # free Google Maps API :)
            data_to_parse = body_data[1].split('"]]],null,[[[')[0]
            # Apply all cleaning patterns in one pass
            cleaning_patterns = [
                (r'null,', ''),  # Remove null values
                (r'dir-tt-?', ''),  # Remove dir-tt patterns
                (r'"https?://\S+",', ''),  # Remove HTTP URLs
                (r'"//maps.gstatic\S+",', ''),  # Remove map static URLs
                (r'\\u[0-9a-fA-F]{4}', ''),  # Remove Unicode escapes
                (r'"[A-Za-z0-9_-]+",', ''),  # Remove quoted alphanumeric strings
                (r'[\\[\]]', ''),  # Remove special characters
                (r'-?[0-9]+\.?[0-9]+,', ''),  # Remove decimal numbers
                (r'[0-9]+,', ''),  # Remove integers
                (r'"[A-Za-z0-9/:+_-]+",', ''),  # Remove quoted alphanumeric strings
                (r'"', '')  # Remove double quotes
            ]
            for pattern, replacement in cleaning_patterns:
                data_to_parse = re.sub(pattern, replacement, data_to_parse)
            final_data = data_to_parse
        else:
            final_data = f"Cannot parse the output data for '{GOOGLE_MAPS_URL}/{start_point}/{end_point}' page"
    except Exception as e:
        print(f"An error occurred while attempting to get traffic data from google maps: {e}")

    return f"{final_data}"
