###### Email Assistant


##### General setup
#### Import libraries
### General libraries
import os, operator
from dotenv import load_dotenv
### Langgraph libraries
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool 
from langchain.agents import create_agent
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
### Typing libraries
from typing import Optional, Literal
from typing_extensions import TypedDict, Literal, Annotated
### Tool libraries
from pydantic import BaseModel, Field
from IPython.display import Image
from PIL import Image as PImage
from datetime import datetime, timezone, timedelta
### Prompt libraries
from prompts import *
### Gmail API Libraries
from google.oauth2.credentials import Credentials  
    # Used to work with Gmail API once credentials are formed
from google.auth.transport.requests import Request
    # Used to request a new API once old one expires
from google_auth_oauthlib.flow import InstalledAppFlow
    # Gathers credentials from local file
from googleapiclient.discovery import build
    # Buils the GMail API client
from googleapiclient.errors import HttpError
    # USed to display errors
from email.message import EmailMessage
import base64

#### Setup models
llm = init_chat_model()

#### Setup profile, general prompt, and sample email
profile = {
    "name": "John",
    "full_name": "John Doe",
    "user_profile_background": "Senior software engineer leading a team of 5 developers",
}

prompt_instructions = {
    "triage_rules": {
        "ignore": "Marketing newsletters, spam emails, mass company announcements",
        "notify": "Team member out sick, build system notifications, project status updates",
        "respond": "Direct questions from team members, meeting requests, critical bug reports",
    },
    "agent_instructions": "Use these tools when appropriate to help manage John's tasks efficiently."
}

email = { # Example incoming email
    "from": "Alice Smith <alice.smith@company.com>",
    "to": "John Doe <john.doe@company.com>",
    "subject": "Quick question about API documentation",
    "body": """
Hi John,

I was reviewing the API documentation for the new authentication service and noticed a few endpoints seem to be missing from the specs. Could you help clarify if this was intentional or if we should update the docs?

Specifically, I'm looking at:
- /auth/refresh
- /auth/validate

Thanks!
Alice""",
}


##### Creating email tool functions
#### Scope of gmail api
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events.owned",
]
#### Gathering credentials
def gather_credentials():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds

    
#### Writing emails
def write_email(
    to: str,
    subject: str,
    content: str,
) -> str:
    creds = gather_credentials()
    try:
        service = build("gmail", "v1", credentials=creds)
        message = EmailMessage()

        message.set_content(content)

        message["To"] = to
        message["From"] = "jparra2357@gmail.com"
        message["Subject"] = subject

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"raw": encoded_message}
        # pylint: disable=E1101
        send_message = (
            service.users()
            .messages()
            .send(userId="me", body=create_message)
            .execute()
        )
        print(f'Message Id: {send_message["id"]}')
    except HttpError as error:
        print(f"An error occurred: {error}")
    return f"Email sent to {to} with subject '{subject}'"


#### Schedule meetings
def schedule_event(
    attendees: dict[str, str], 
    subject: str, 
    duration_minutes: int, 
    preferred_day: str
) -> str:
    creds = gather_credentials()
    try: 
        service = build("calendar", "v3", credentials=creds)

        ### Configure dates
        date = preferred_day.split("/")
        date = [int(item) for item in date]
            # Assuming mm/dd/yyyy
        start = datetime(date[2], date[0], date[1], 8, 0, tzinfo=timezone.utc).isoformat()
        end = datetime(date[2], date[0], date[1], 8, int(duration_minutes), tzinfo=timezone.utc).isoformat()



        ### Create the events
        event = {
            'summary': subject,
            # 'location': '800 Howard St., San Francisco, CA 94103',
            # 'description': 'A chance to hear more about Google\'s developer products.',
            'start': {
                'dateTime': start,
                'timeZone': 'America/New_York',
            },
            'end': {
                'dateTime': end,
                'timeZone': 'America/New_York',
            },
            # 'recurrence': [
            #     'RRULE:FREQ=DAILY;COUNT=2'
            # ],
            'attendees': [attendees],
            # 'reminders': {
            #     'useDefault': False,
            #     'overrides': [
            #         {'method': 'email', 'minutes': 24 * 60},
            #         {'method': 'popup', 'minutes': 10},
            #     ],
            # },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"Event created: {event.get('htmlLink')}")
    except HttpError as error:
        print(f"An error occured: {error}")
    return f"Meeting '{subject}' scheduled for {preferred_day} with {len(attendees)} attendees"


        


def check_day_availability(
    start: str, # Will be in ISO format
    end: str,   # Will be in ISO format
    event_duration: int = 30,
) -> str:
    # Pydantic model can be done with field validator, see C17V
    creds = gather_credentials()
    try:
        service = build("calendar", "v3", credentials=creds)
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start,
                timeMax=end,
                # maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        day_datetime = datetime.fromisoformat(start)
        day = day_datetime.strftime("%b %d")

        if not events:
            print('no events')
            return f"Available on {day} from 700 to 1700"
        
        duration_delta = timedelta(minutes  = event_duration)
        entry_time = 700
        exit_time = 1700
        add_entry, add_exit = True, True 
        available_times = {
            "start":[],
            "end": [],
        }

        for i, event in enumerate(events):
            print(f"Working with event {i}:") 

            ### Getting the start and end times of the planned event
            planned_event_start = event["start"].get("dateTime", event["start"].get("date"))
            planned_event_end = event["end"].get("dateTime", event["end"].get("date"))
            
            print(f"Event {i} start: {planned_event_start}")
            print(f"Event {i} end: {planned_event_end}")
            
            ### Transforming times into datetime iso format
            start_datetime = datetime.fromisoformat(planned_event_start)
            end_datetime = datetime.fromisoformat(planned_event_end)

            ### Adding the event duration to the already planned events
                # This yields the latest available to start the new event
                # Note: latest avaialbility for new event 
                        # = start time of planned event - new event's duration
            latest_availability = start_datetime - duration_delta
            latest_availability = int(
                f"{latest_availability.hour}{latest_availability.minute:0>2d}"
            )
            
            ### Calculating the earliest availability to start new event
                # NOte: earliest availability = end of the planned event
            earliest_avaialability = int(
                f"{end_datetime.hour}{end_datetime.minute:0>2d}"
            )
            
            ### Edge cases
            if latest_availability < entry_time and earliest_avaialability > exit_time:
                # This would be an event that takes up the whole day
                # Ex: 600 - 1800
                print(f'CASE A - {latest_availability} and {earliest_avaialability}')
                break
            elif latest_availability > exit_time or earliest_avaialability < entry_time:
                # IF the end of a meeting happens BEFORE 7AM, then 
                        # it wouldn't matter registering the start of 
                        # that meeting, since it would ALSO be before
                        # 7 AM
                    # The same can be said if beginning of event is 
                            # AFTER 1700, end of day
                # Ex: meeting 5am - 630am
                    # End @ 630 am => continue to next event
                # Ex: 1800 - 1900
                    # Start @ 1800 > 1700 = > continue to next eventx
                print(f'CASE B - {latest_availability} and {earliest_avaialability}')
                continue
            elif latest_availability < entry_time and earliest_avaialability > entry_time:
                # This is the case for when the event starts before entry time
                        # but it ends after the entry time
                # EX: 600 - 800
                # In this case, we won't add 700 to available start times
                    # Since the earliest start time starts at 800
                print(f'CASE C - {latest_availability} and {earliest_avaialability}')
                add_entry = False
                available_times["start"].append(earliest_avaialability)
            elif latest_availability < exit_time and earliest_avaialability > exit_time:
                # This is when an event starts before exit time but ends afterwards
                # EX: 1600 - 1800
                # In this case we won't add 1700 to available end times
                    # Since the latest time for availbility if 1600 - meeting_duration
                print(f'CASE D - {latest_availability} and {earliest_avaialability}')
                add_exit = False
                available_times["end"].append(latest_availability)
            else:
                available_times["start"].append(earliest_avaialability)
                available_times["end"].append(latest_availability)

        
        ### Adding the beggining of the day and end of the day
        if add_entry: available_times['start'].insert(0, entry_time)
        if add_exit: available_times['end'].append(exit_time)
           
        ### Base check
        # for i, event in enumerate(events):
        #     start = event["start"].get("dateTime", event["start"].get("date"))
        #     end = event["end"].get("dateTime", event["end"].get("date"))
        #     print(f"Event {i} start: {start}")
        #     print(f"Event {i} end: {end}")

    except HttpError as error:
        print(f"Error occured: {error}")

    result = f"Available times on {day} are:\n"
    event_duration = (event_duration / 60) * 100
    for start, end in zip(available_times['start'], available_times['end']):
        if start + event_duration > exit_time : break
        if start > end : 
            print('CONTINUING')
            continue
        result += f"{start} to {end}\n"

    print(result)
    return result


#### General availability checker tool
def check_availability(
    start: datetime, 
    end: datetime,
    event_duration: int = None,
) -> str:
    start = datetime.fromisoformat(start)
    end = datetime.fromisoformat(end)
    day_diff = start - end
    day_delta = timedelta(days = 1)
    return




#### Checking that the tools work as intended
### First tool
# print(write_email('jparra2357@gmail.com', 'integracion', 'probando la integracion de api'))
    # works
### Second tool
# print(schedule_meeting(
#     {'email': 'jparra2357@gmail.com'},
#     "Nuevo evento",
#     "30",
#     "12/23/2025",
#         # Note: bs ubuntu thinks i'm in a diff timezone, timing might be off
# ))
    # works
### Third tool
check_day_availability(
    '2025-12-22T00:00:00-05:00',
    '2025-12-23T00:00:00-05:00',
    30
)





















