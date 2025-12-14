##### Email Assistant
    # Will contain the base code from Course 8
    # Mainly invovles semantic, procedural, episodic long-term mem
    # Objectives:
        # Integrate with short-term mem
            # For StateSnapshot analysis
        # Fill in with real APIs from Gmail


##### General setup
#### Import libraries
import os, operator
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing_extensions import TypedDict, Literal, Annotated
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool   #Decorator
from langchain.agents import create_agent
from prompts import *
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from typing import Literal
from IPython.display import Image
from PIL import Image as PImage
from datetime import datetime, timezone
    #class datetime.datetime(year, month, day, hour=0, minute=0, 
    # second=0, microsecond=0, tzinfo=None, *, fold=0)

#### Setting up models
llm = init_chat_model()


#### Setup profile, GENERAL prompt, and example email
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








##### Creating Router - simple agent
#### Creating pydantic models
class Router(BaseModel):
    """Analyze the unread email and route it according to its content."""

    reasoning: str = Field(
        description="Step-by-step reasoning behind the classification."
    )
        # Reasoning behind why LLM made the decision it chose
    classification: Literal["ignore", "respond", "notify"] = Field(
        description="The classification of an email: 'ignore' for irrelevant emails, "
        "'notify' for important information that doesn't need a response, "
        "'respond' for emails that need a reply",
    )
        # Should be 1 of 3 categories in "triage_rules" line 17

#### Connect the pydantic model to the router simple-agent
llm_router = llm.with_structured_output(Router, include_raw = True)

#### Creating prompts for router
system_prompt = triage_system_prompt.format(
    full_name=profile["full_name"],
    name=profile["name"],
    examples=None,
    user_profile_background=profile["user_profile_background"],
    triage_no=prompt_instructions["triage_rules"]["ignore"],
    triage_notify=prompt_instructions["triage_rules"]["notify"],
    triage_email=prompt_instructions["triage_rules"]["respond"],
)
user_prompt = triage_user_prompt.format(
    author=email["from"],
    to=email["to"],
    subject=email["subject"],
    email_thread=email["body"],
)

#### Running router simple-agent on our sample email
# result = llm_router.invoke(
#     [
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": user_prompt},
#     ]
# )




##### Create tools
#### GMail API overview: 
    # https://developers.google.com/workspace/gmail/api/guides
        # Overview guide
    # https://console.cloud.google.com/home/dashboard?project=working-with-python-481113&supportedpurview=project,folder
        # Dashboard 1
    # https://console.cloud.google.com/apis/api/gmail.googleapis.com/metrics?project=working-with-python-481113    
        # Dashboard 2
    # https://console.cloud.google.com/auth/overview?project=working-with-python-481113    
        # OAuth site
    # https://developers.google.com/workspace/gmail/api/quickstart/python
        # Quick start with Python
#### Setting the API scope and gmail libraries

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

# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events.owned",
]
#### Creating the tools
# @tool
def write_email(to: str, subject: str, content: str) -> str:
    """Write and send an email."""
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

# @tool
def schedule_meeting(
    attendees: dict[str, str], 
    subject: str, 
    duration_minutes: int, 
        # For now assume <60 mins
    preferred_day: str
) -> str:
    """Schedule a calendar meeting."""
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
    return f"Meeting '{subject}' scheduled for {preferred_day} with {len(attendees)} attendees"

@tool
def check_calendar_availability(day: str) -> str:
    #TODO: create a pydantic model that will have correct day formattings
        # Ex
    # class CheckDates(BaseModel):
    #     start_year: int
    #     start_month: int
    #     start_date: int
    #     end_year: Optional[int]
    #     end_month: Optional[int]
    #     end_date: Optional[int]
        # That way it'll be easier to put into check calendar on any day
    """Check calendar availability for a given day."""
    # Placeholder response - in real app would check actual calendar
    return f"Available times on {day}: 9:00 AM, 2:00 PM, 4:00 PM"


#### Checking that the tools work as intended
# print(write_email('jparra2357@gmail.com', 'integracion', 'probando la integracion de api'))
print(schedule_meeting(
    {'email': 'jparra2357@gmail.com'},
    "Nuevo evento",
    "30",
    "12/23/2025",
        # Note: bs ubuntu thinks i'm in a diff timezone, timing might be off
))



# print(dir(llm))
# print(dir(llm.get_graph()))
# print(llm.get_graph())
# print(llm.get_graph().draw_ascii())

# def random():
#     return

# new_llm = llm.get_graph().add_node('random', random)


#### Visualize agent
### Using ASCII
# print(agent.graph.get_graph().draw_ascii())
# print('\n' + '=' * 50 + '\n')
### Using PIL and Image
# img2 = Image(agent.graph.get_graph(xray=True).draw_mermaid_png())
# pimg = PImage.open(io.BytesIO(img2.data))
# # pimg.show()
# pimg.save('agent_graph.jpg')









def main():
    print("DONE")


if __name__ == "__main__":
    main()
