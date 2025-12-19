###### Email Assistant


##### General setup
#### Import libraries
### General libraries
import os, operator
from dotenv import load_dotenv
from utilities_clean import *
### Langgraph libraries
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool 
from langchain.agents import create_agent
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from langchain_core.messages import SystemMessage, HumanMessage,\
    AIMessage, ToolMessage
### Typing libraries
from typing import Optional, Literal, List
from typing_extensions import TypedDict, Literal, Annotated
### Tool libraries
from pydantic import BaseModel, Field, field_validator
from IPython.display import Image
from PIL import Image as PImage
from datetime import datetime, timezone, timedelta
### Model libraries
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.sqlite import SqliteSaver
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

#### Get APIs
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")


#### Setup models
llm = ChatGoogleGenerativeAI(
    api_key = google_api_key,
    model = "gemini-2.5-flash-lite",
)

#### Setting up DB storage utility
DB_NAME = "output.sqlite"
TABLE_NAME = "email_assistant"
storage = Storage(DB_NAME, TABLE_NAME)


#### Creating memories
### Short-term memories
conn = sqlite3.connect('checkpoints.sqlite', check_same_thread=False)
    #"check_same_thread = False" => enables multi-thread usage
memory = SqliteSaver(conn)



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
#### Creating Pydantic model for the tools
### For "check_avaialbility"
class TimeAvailability(BaseModel):
    start: str = Field(
        description="Moment at which to start calendar check (format = 'YYYY-MM-DDTHH:MM:SS+/-HH:MM')"
    )
    end: str = Field(
        description="Moment at which to end calendar check (format = 'YYYY-MM-DDTHH:MM:SS+/-HH:MM')"
    )
    event_duration: Optional[int] = Field(
        default=30,
        description="Used to tell the duration of the event"
    )
    @field_validator("start", "end")
    def validate_time(cls, time: str):
        import re
        pattern = r"^20[2-9]{1}[0-9]{1}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\+|\-)?\d{2}:\d{2}$"
            # Patterns ensures year will be 2020+
        if not re.match(pattern, time):
            raise ValueError("time needs to be in ISO format string")
        return time

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


#### Getting emails
def getEmails() -> dict:
    creds = gather_credentials()
    to_return = {}
    try:
        service = build('gmail', 'v1', credentials=creds)
        results = (
            service.users().messages()
            .list(maxResults = 6, userId="me", labelIds=["INBOX"])
                #Note: technically "INBOX" shows "ALL MAIL" mail
            .execute()
        )

        messages = results.get("messages", [])
        if not messages:
            print("No messages found.")
            return to_return
    
    except HttpError as error:
        print(f"Error: {error}")

    for msg in messages:
        txt = (
            service.users().messages()
            .get(userId="me", id=msg["id"]).execute()
        )
        try:
            payload = txt['payload']
            headers = payload['headers']
            body = payload['body']
            parts = payload['parts']
        except: continue
        for data in headers:
            if data['name'] == 'Subject':
                to_return["subject"] = data['value']
            if data['name'] == "From":
                to_return["author"] = data['value']
            if data['name'] == 'To':
                to_return["to"] = data['value']
        encoded_body = parts[0]['body']['data']
        encoded_body = encoded_body.replace("-","+").replace("_","/")
            #Necessary to decode the email properly
        decoded_data = base64.b64decode(encoded_body)
        decoded_data = decoded_data.decode('utf-8')
        to_return['email_thread'] = decoded_data
        break
    
    return to_return


#### Writing emails
@tool
def write_email(
    to: str,
    subject: str,
    content: str,
) -> str:
    """Write and send an email"""
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
@tool
def schedule_event(
    attendees: dict[str, str], 
    subject: str, 
    duration_minutes: int, 
    preferred_day: str
) -> str:
    """Schdule a meeting on google calendar"""
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


        

#### Checking avaialbility
def check_day_availability(
    start: datetime, 
    end: datetime,  
    event_duration: int = 30,
) -> str:
    # Pydantic model can be done with field validator, see C17V
    creds = gather_credentials()
    day = start.strftime("%b %d")
    try:
        service = build("calendar", "v3", credentials=creds)
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=start.isoformat(),
                timeMax=end.isoformat(),
                # maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])
    
    except HttpError as error:
        print(f"Error occured: {error}")

    if not events:
        print(f"Available on {day} from 700 to 1700\n")
        return f"Available on {day} from 700 to 1700\n"
    
    duration_delta = timedelta(minutes  = event_duration)
    entry_time = 700
    exit_time = 1700
    add_entry, add_exit = True, True 
    available_times = {
        "start":[],
        "end": [],
    }

    for i, event in enumerate(events):
        ### Getting the start and end times of the planned event
        planned_event_start = event["start"].get("dateTime", event["start"].get("date"))
        planned_event_end = event["end"].get("dateTime", event["end"].get("date"))
        
        
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
            continue
        elif latest_availability < entry_time and earliest_avaialability > entry_time:
            # This is the case for when the event starts before entry time
                    # but it ends after the entry time
            # EX: 600 - 800
            # In this case, we won't add 700 to available start times
                # Since the earliest start time starts at 800
            add_entry = False
            available_times["start"].append(earliest_avaialability)
        elif latest_availability < exit_time and earliest_avaialability > exit_time:
            # This is when an event starts before exit time but ends afterwards
            # EX: 1600 - 1800
            # In this case we won't add 1700 to available end times
                # Since the latest time for availbility if 1600 - meeting_duration
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



    result = f"Available times on {day} are:\n"
    event_duration_percentage = (event_duration / 60) * 100
    for start, end in zip(available_times['start'], available_times['end']):
        if start + event_duration_percentage > exit_time : break
        if start >= end: continue
        result += f"{start} to {end}\n"

    print(f"Iterated: {result}")
    return result


#### General availability checker tool
@tool(args_schema=TimeAvailability)
def check_availability(
    start: str, # Will be in iso format
    end: str,   # Will be in iso format
    event_duration: int = None,
) -> str:
    """Check avaialable timings by referencing a Google calendar"""
    start = datetime.fromisoformat(start)
    end = datetime.fromisoformat(end)
    day_diff = end - start
    day_diff = day_diff.days
    day_delta = timedelta(days = 1)
    tmp_start = start
    tmp_end = start + day_delta
    result = ""
    for i in range(day_diff):
        result += check_day_availability(tmp_start, tmp_end, event_duration)
        result += '\n'
        tmp_start = tmp_end
        tmp_end = tmp_end + day_delta
    print(f"FINAL: {result}")
    return result







































##### Creating agents
#### Router agent
### Pydantic model
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

### Creating model with pydantic
llm_router = llm.with_structured_output(Router, include_raw = True)

### Creating prompts for router
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




#### Responder agent
### Creating system prompt
def react_sys_prompt():
    content = agent_system_prompt.format(
        instructions=prompt_instructions["agent_instructions"],
        **profile
    )
    return SystemMessage(content=content)

### Assembling responder agent
tools=[write_email, schedule_event, check_availability]
responder_agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=react_sys_prompt(),
)











































##### Creating email assistant MAS
#### Creating the agent's state
class AgentState(TypedDict):
    email_input: dict
    messages: Annotated[List[AnyMessage], operator.add]
    metrics: Annotated[dict[str, dict[str,int]], operator.or_]

#### Creating nodes
### Router node
def router_node(state: AgentState) -> Command[
    Literal["responder", "__end__"]
]:
    ## Creating metrics for email assistant to use
    metrics = Metrics()

    ## Setting up the email to be sent to agent
    author = state['email_input']['author']
    to = state['email_input']['to']
    subject = state['email_input']['subject']
    email_thread = state['email_input']['email_thread']

    ## Setting up router's system prompt
    system_prompt = triage_system_prompt.format(
        full_name=profile["full_name"],
        name=profile["name"],
        user_profile_background=profile["user_profile_background"],
        triage_no=prompt_instructions["triage_rules"]["ignore"],
        triage_notify=prompt_instructions["triage_rules"]["notify"],
        triage_email=prompt_instructions["triage_rules"]["respond"],
        examples=None
    )

    ## Setting up router's user prompt
    user_prompt = triage_user_prompt.format(
        author=author, 
        to=to, 
        subject=subject, 
        email_thread=email_thread
    )

    ## Invoking the router
    result = llm_router.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )

    ## Analyzing the invoked metrics
    ai_msg = result['raw']
    extract = metrics.extract_tokens_used(ai_msg, "router_node")
    metrics = metrics.aggregate(extract)
    print('router metrics')
    print(metrics.history)
    print('\n' + '=' * 50 + '\n')
    metrics_update = {
        "metrics": metrics.history
    }

    ## Setting up next graph traversal steps
    result = result['parsed']
    if result.classification == "respond":
        print("📧 Classification: RESPOND - This email requires a response")
        goto = "responder"
        update = metrics_update | {
            "messages": [
                HumanMessage(content=f"Respond to the email {state['email_input']}"),
            ]
        }
    elif result.classification == "ignore":
        print("🚫 Classification: IGNORE - This email can be safely ignored")
        update = metrics_update
        goto = END
    elif result.classification == "notify":
        # If real life, this would do something else
        print("🔔 Classification: NOTIFY - This email contains important information")
        update = metrics_update
        goto = END
    else:
        raise ValueError(f"Invalid classification: {result.classification}")
    return Command(goto=goto, update=update)

### Responder node
def responder_node(state: AgentState):
    ## Creating metrics for email assistant to use
    metrics = Metrics()
    ## Extract user prompt from agent state
    user_prompt = state['messages'][-1]
    ## Invoke agent with user prompt
    response = responder_agent.invoke(
        {"messages": [user_prompt]}
    )
        # It will return the following format:
            #response = {"message": [AnyMessage]}
    ## Analyzing metrics used
    for i, msg in enumerate(response['messages']):
        # print(msg)
        if (type(msg) != AIMessage): continue
        extract = metrics.extract_tokens_used(msg, f"responder_node_{i}")
        metrics = metrics.aggregate(extract)
    ## Update the agent state with messages
    print(f"Responder response: {response}\n\n")

    return {"messages": [response], "metrics": metrics.history}


#### Assembling the email assistant graph
email_agent = StateGraph(AgentState)
email_agent = email_agent.add_node("router", router_node)
email_agent = email_agent.add_node("responder", responder_node)
email_agent = email_agent.add_edge(START, "router")
email_agent = email_agent.compile(
    checkpointer=memory,
)
































##### Working with the email assistant
#### Getting desired email
# email = getEmails()
# print(email)

# check_availability(
#     '2025-12-22T00:00:00-05:00',
#     '2025-12-26T00:00:00-05:00',
#     30
# )

current_thread = 5

#### Setting up config
config = {
    'configurable':{
        'thread_id': str(current_thread),
    }
}

#### Invoking and saving response
# response = email_agent.invoke({'email_input': email}, config)
# storage.save_data(response, current_thread, "calendar_availability")
# print(response)


# response = storage.retrieve_data(3)
# print(response['messages'])
# for i, msg in enumerate(response['messages'][1]['messages']):
#     print(f"Msg {i}: \n{msg}\n\n")
# print('\n\n\n')
# print(email_agent.get_state(config))

#### Checking snapshot history
# analyzer = Analyzer()
# display_fields = {
#     # "config",
#     # "parent_config",
#     # "next",
#     "values"
# }

# config = {
#     'configurable':{
#         'thread_id': str(2),
#         'checkpoint_ns': "",
#     }
# }
# # print(email_agent.get_state(config))
# main_history = email_agent.get_state_history(config)
# hist_list = list(main_history)
# print('MAIN HISTORY\n\n')
# analyzer.analyze_history(hist_list, display_fields)


# config = {
#     'configurable':{
#         'thread_id': str(2),
#         'checkpoint_ns': "responder:04b6dff5-8034-d10f-2268-6940beb5e892"
#     }
# }
# react_history = email_agent.get_state_history(config)
# hist_list = list(react_history)
# print("\n\n\n\n###############REPSONDER HISTORY###############\n\n\n\n")
# analyzer.analyze_history(hist_list, display_fields)














