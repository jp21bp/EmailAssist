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
from typing import Optional, Literal
from typing_extensions import TypedDict, Literal, Annotated
from langchain_core.messages import SystemMessage
from langchain.chat_models import init_chat_model
from langchain_core.tools import tool   #Decorator
from langchain.agents import create_agent
    # https://reference.langchain.com/python/langchain/agents/#langchain.agents.create_agent
from prompts import *
from utilities_clean import *
from bs4 import BeautifulSoup
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.graph import StateGraph, START, END
from langgraph.types import Command
from IPython.display import Image
from PIL import Image as PImage
from langchain_google_genai import ChatGoogleGenerativeAI
from datetime import datetime, timezone, timedelta
    #class datetime.datetime(year, month, day, hour=0, minute=0, 
    # second=0, microsecond=0, tzinfo=None, *, fold=0)

### Getting APIs
load_dotenv()
google_api_key = os.getenv("GOOGLE_API_KEY")


#### Setting up models
llm = ChatGoogleGenerativeAI(
    api_key = google_api_key,
    model = "gemini-2.5-flash-lite",
)

#### Setting up DB storage utility
DB_NAME = "output.sqlite"
TABLE_NAME = "email_assistant"
storage = Storage(DB_NAME, TABLE_NAME)

#### Creating memories
### Short-term memory
conn = sqlite3.connect('checkpoints.sqlite', check_same_thread=False)
    #"check_same_thread = False" => enables multi-thread usage
memory = SqliteSaver(conn)





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


#### Getting emails
def getEmails():
    creds = gather_credentials()
    try: 
        service = build('gmail', 'v1', credentials=creds)
        results = (
            service.users().messages().list(maxResults = 15, userId="me", labelIds=["INBOX"]).execute()
                #Note: technically "INBOX" shows "ALL MAIL" mail
                    # I.e., it isnt exclusive only to mails that are in inbox
                    # for some reason it shows all mail
                    # need to investigate if there's a way fpor me to only gilter the invox mail
                    # at the same time, there is no prioblem in filtering through all mail
                    # It will simply take a bit longer to process

        )
        messages = results.get("messages", [])

        if not messages:
            print("No messages found.")
            return
        
        for i, msg in enumerate(messages):
            if i != 0: continue

            txt = (
                service.users().messages().get(userId="me", id=msg["id"]).execute()
            )

            ### Creating webpage simulation of email
            # try:
            #     encoded_data = txt['payload']['body']['data']
            #     # print(f'FIRST ENCODED DATA: {encoded_data}')
            # except: pass

            # try:
            #     encoded_data = txt['payload']['parts'][1]['body']['data']
            #     # print(f'SECOND ENCODED DATA: {encoded_data}')
            # except: pass

            # try:
            #     encoded_data = txt['payload']['parts'][0]['parts'][0]['body']['data']
            #     # print(f'THIRD ENCODED DATA: {encoded_data}')
            # except: pass

            # encoded_data = encoded_data.replace("-","+").replace("_","/")
            #     #Necessary to decode the email properly
            # decoded_data = base64.b64decode(encoded_data)
            # # print(decoded_data)
            # soup = BeautifulSoup(decoded_data , "html.parser")
            # # body = soup.body()
            # # main = soup.find('main')
            # # print(main)

            # with open('output.html', 'w') as file:
            #     file.write(str(soup))
            #         #SHOWS NICE HTML WEBPAGE



            ### Extracting: author, subject, to, email_thread
            result = {}
            payload = txt['payload']
            headers = payload['headers']
            body = payload['body']
            parts = payload['parts']
            # print(txt.keys())
            # print('='*30)
            # print(payload.keys())
            # print('='*30)
            # print(headers)
            # print('='*30)
            # print(body)
            # print('='*30)
            # print(parts[0])
            # print('='*30)
            # print(parts[1])
            # print('='*30)
            for data in headers:
                if data['name'] == 'Subject':
                    result["subject"] = data['value']
                if data['name'] == "From":
                    result["author"] = data['value']
                if data['name'] == 'To':
                    result["to"] = data['value']

            encoded_body = parts[0]['body']['data']
            encoded_body = encoded_body.replace("-","+").replace("_","/")
                #Necessary to decode the email properly
            decoded_data = base64.b64decode(encoded_body)
            decoded_data = decoded_data.decode('utf-8')
            result['email_thread'] = decoded_data
            break


    except HttpError as error:
        print(f"Error: {error}")

    return result



    
#### Writing emails
@tool
def write_email(
    to: str,
    subject: str,
    content: str,
) -> str:
    """Write an email to a subject"""
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
@tool
def schedule_event(
    attendees: dict[str, str], 
    subject: str, 
    duration_minutes: int, 
    preferred_day: str
) -> str:
    """ Schedule an event on Google calendar"""
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
    start: datetime, 
    end: datetime,  
    event_duration: int = 30,
) -> str:
    # TO FIX: Current, the times showing are the times at which the meeting could start
        # However, this can cause confusion when the user is seeing the times
        # They can mistake 11:45 - 11:50 as if the meeting can only last 5 mins
            # However, this actually means that the meeting can start at ANYTIME during 
                    # range, and still not conflict with other planned events
        # The fix will need to be able to display non confusing timings
    # Pydantic model can be done with field validator, see C17V
    print(f"{start} - {end}")
    creds = gather_credentials()
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

        # day_datetime = datetime.fromisoformat(start)
        # day = day_datetime.strftime("%b %d")


        day = start.strftime("%b %d")

        if not events:
            print(f"Available on {day} from 700 to 1700")
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

            ### Creating str time for latest_availability
                # I.e., this is what will be displayed in the outcome of avaialble times
                # It will erase confusion as to when meetings should be arranged
                # Ex: 45 minute meeting => available time 1145 - 1150
                    # Avaialble gap is 5 minutes, but event can begin at ANY TIME
                            # DURING those 5 mins that won't overlap into other planned events
            latest_to_display = int(
                f"{start_datetime.hour}{start_datetime.minute:0>2d}"
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
    event_duration_percentage = (event_duration / 60) * 100
    for start, end in zip(available_times['start'], available_times['end']):
        if start + event_duration_percentage > exit_time : break
        if start >= end: 
            print('CONTINUING')
            continue
        result += f"{start} to {end}\n"

    print(result)
    return result


#### General availability checker tool
@tool
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
    # print(day_diff)
    day_delta = timedelta(days = 1)
    # print(day_delta)
    tmp_start = start
    tmp_end = start + day_delta
    for i in range(day_diff):
        check_day_availability(tmp_start, tmp_end, event_duration)
        # print(f"{tmp_start} - {tmp_end}")
        tmp_start = tmp_end
        tmp_end = tmp_end + day_delta
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
# check_availability(
#     '2025-12-21T00:00:00-05:00',
#     '2025-12-24T00:00:00-05:00',
#     30
# )































###  Turn ambigous prompt for the main single-agent into specific prompt
## Importing ambiguous prompt for main agent
def react_sys_prompt():
    content = agent_system_prompt.format(
        instructions=prompt_instructions["agent_instructions"],
        **profile
    )
    return SystemMessage(content=content)




### Assembling main state-agent
tools=[write_email, schedule_event, check_availability]
responder_agent = create_agent(
    model=llm,
    tools=tools,
    system_prompt=react_sys_prompt(),
)

# print(dir(agent))


### invoking the main state agent
# response = agent.invoke(
#     {"messages": [{
#         "role": "user", 
#         "content": "what is my availability for tuesday?"
#     }]}
# )
# response["messages"][-1].pretty_print()































##### Creating email assistant MAS
#### Creating the agent's state
class AgentState(TypedDict):
    email_input: dict
    messages: Annotated[list, operator.add]

#### Creating nodes
### Router node
def router_node(state: AgentState) -> Command[
    Literal["responder", "__end__"]
]:
    author = state['email_input']['author']
    to = state['email_input']['to']
    subject = state['email_input']['subject']
    email_thread = state['email_input']['email_thread']

    system_prompt = triage_system_prompt.format(
        full_name=profile["full_name"],
        name=profile["name"],
        user_profile_background=profile["user_profile_background"],
        triage_no=prompt_instructions["triage_rules"]["ignore"],
        triage_notify=prompt_instructions["triage_rules"]["notify"],
        triage_email=prompt_instructions["triage_rules"]["respond"],
        examples=None
    )
    user_prompt = triage_user_prompt.format(
        author=author, 
        to=to, 
        subject=subject, 
        email_thread=email_thread
    )
    result = llm_router.invoke(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    result = result['parsed']
    if result.classification == "respond":
        print("📧 Classification: RESPOND - This email requires a response")
        goto = "responder"
        update = {
            "messages": [
                {
                    "role": "user",
                    "content": f"Respond to the email {state['email_input']}",
                }
            ]
        }
    elif result.classification == "ignore":
        print("🚫 Classification: IGNORE - This email can be safely ignored")
        update = None
        goto = END
    elif result.classification == "notify":
        # If real life, this would do something else
        print("🔔 Classification: NOTIFY - This email contains important information")
        update = None
        goto = END
    else:
        raise ValueError(f"Invalid classification: {result.classification}")
    return Command(goto=goto, update=update)

### Responder node
def responder_node(state: AgentState):
    return


#### Assembling the email assistant graph
    # Not going to use python "class"
        # Main benefit - modularity
            # I can create the node's fcnality in other files
            # Can import those node fcnalities into this file
            # Use imports directly, w.o./ having to put inside "class"

email_agent = StateGraph(AgentState)
email_agent = email_agent.add_node("router", router_node)
email_agent = email_agent.add_node("responder", responder_agent)
email_agent = email_agent.add_edge(START, "router")
email_agent = email_agent.compile(
    checkpointer=memory,
)


#### Visualizing the email assistnat graph
# print(dir(email_agent))
print(email_agent.get_graph().draw_ascii())



# email = getEmails()
# config = {
#     'configurable':{
#         'thread_id': str(1),
#     }
# }
# response = email_agent.invoke({'email_input': email}, config)
# for m in response['messages']:
#     m.pretty_print()

# storage.save_data(response, 1, "test_response_1")

























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
