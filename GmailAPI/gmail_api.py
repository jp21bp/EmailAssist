##### Gmail API file
    # This file will be related to the usage of Gmail API
    # The end goal will be to use this API in the email assistant
    # The gmail that will be used is "jparra2357"
        # Since it's not widely used

#### Main website tracker
    # https://console.cloud.google.com/home/dashboard?project=working-with-python-481113&supportedpurview=project,folder
        # Dashboard 1
    # https://console.cloud.google.com/apis/api/gmail.googleapis.com/metrics?project=working-with-python-481113    
        # Dashboard 2
    # https://console.cloud.google.com/auth/overview?project=working-with-python-481113    
        # OAuth site
    # https://developers.google.com/workspace/gmail/api/quickstart/python
        # Quick start with Python



from google.auth.transport.requests import Request
    # Used to request a new API once old one expires
from google.oauth2.credentials import Credentials  
    # Used to work with Gmail API once credentials are formed
from google_auth_oauthlib.flow import InstalledAppFlow
    # Gathers credentials from local file
from googleapiclient.discovery import build
    # Buils the GMail API client
from googleapiclient.errors import HttpError
    # USed to display errors


import os.path
import base64
import google.auth
import datetime
    #class datetime.datetime(year, month, day, hour=0, minute=0, 
    # second=0, microsecond=0, tzinfo=None, *, fold=0)
from bs4 import BeautifulSoup
from email.message import EmailMessage


# If modifying these scopes, delete the file token.json.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/calendar.events.owned",
]


def main():
    """Shows basic usage of the Gmail API.
    Lists the user's Gmail labels.
    """
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
        # Call the Gmail API
        service = build("gmail", "v1", credentials=creds)
        results = service.users().labels().list(userId="me").execute()
        labels = results.get("labels", [])

        if not labels:
            print("No labels found.")
            return
        print("Labels:")
        for label in labels:
            print(label["name"])

    except HttpError as error:
        # TODO(developer) - Handle errors from gmail API.
        print(f"An error occurred: {error}")



















def getAttachment(service, user_id, msg_id):
    # WORKS, but the attachment file type might affect how fcn performs
    """Get and store attachment from Message with given id.

    :param service: Authorized Gmail API service instance.
    :param user_id: User's email address. The special value "me" can be used to indicate the authenticated user.
    :param msg_id: ID of Message containing attachment.
    """
    try:
        message = service.users().messages().get(userId=user_id, id=msg_id).execute()

        for part in message['payload']['parts']:
            if part['filename']:
                if 'data' in part['body']:
                    data = part['body']['data']
                else:
                    att_id = part['body']['attachmentId']
                    att = service.users().messages().attachments().get(userId=user_id, messageId=msg_id,id=att_id).execute()
                    data = att['data']
                file_data = base64.urlsafe_b64decode(data.encode('UTF-8'))
                path = part['filename']

                with open(path, 'w') as f:
                    f.write(str(file_data))

    except HttpError as error:
        print(f"Downloading attachment error: {error}")























def getEmails():
    # Variable creds will store the user access token.
    # If no valid token found, we will create one.
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
        # Connect to the Gmail API
        service = build('gmail', 'v1', credentials=creds)

        # request a list of all the messages
        # result = service.users().messages().list(userId='me').execute()

        # We can also pass maxResults to get any number of emails. Like this:
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

        print("Messages:")

        # messages is a list of dictionaries where each dictionary contains a message id.
    except HttpError as error:
        print(f"Couldn't create Gmail client: {error}")


    # for i, msg in enumerate(messages):
    #     txt = (
    #         service.users().messages().get(userId="me", id=msg["id"]).execute()
    #     )
    #     print(txt['snippet'])
    #     print('='*30)
    # return


    # iterate through all the messages
    for i, msg in enumerate(messages):
        if i != 0: continue
        # Get the message from its id
        # txt = service.users().messages().get(userId='me', id=msg['id']).execute()
        txt = (
            service.users().messages().get(userId="me", id=msg["id"]).execute()
        )

        # getAttachment(service, "me", msg['id'])
        # return

        print(dir(txt))
        for k,v in txt.items():
            print(k)
            print(v)
            print('='*30)

        print('\n'*3)
        for k,v in txt['payload'].items():
            print(k)
            print(v)
            print('='*30)

        # print('\n' * 3)
        # for item in txt['payload']['headers']:
        #     print(item)
        #     print('='*30)

        # print('\n'*3)
        # for item in txt['payload']['parts']:
        #     print(item)
        #     print('='*30)

        print('\n'*3)

        try:
            encoded_data = txt['payload']['body']['data']
            print(f'FIRST ENCODED DATA: {encoded_data}')
        except: pass

        try:
            encoded_data = txt['payload']['parts'][1]['body']['data']
            print(f'SECOND ENCODED DATA: {encoded_data}')
        except: pass

        try:
            encoded_data = txt['payload']['parts'][0]['parts'][0]['body']['data']
            print(f'THIRD ENCODED DATA: {encoded_data}')
        except: pass

        encoded_data = encoded_data.replace("-","+").replace("_","/")
            #Necessary to decode the email properly
        decoded_data = base64.b64decode(encoded_data)
        # print(decoded_data)

        # print('\n'*3)

        # soup = BeautifulSoup(decoded_data, 'lxml')
        soup = BeautifulSoup(decoded_data , "html.parser")
        # body = soup.body()
        # main = soup.find('main')
        # print(main)

        with open('output.html', 'w') as file:
            file.write(str(soup))
                #SHOWS NICE HTML WEBPAGE

        break
        # # Use try-except to avoid any Errors
        # try:
        #     # Get value of 'payload' from dictionary 'txt'
        #     payload = txt['payload']
        #     headers = payload['headers']

        #     # Look for Subject and Sender Email in the headers
        #     for d in headers:
        #         if d['name'] == 'Subject':
        #             subject = d['value']
        #         if d['name'] == 'From':
        #             sender = d['value']

        #     # The Body of the message is in Encrypted format. So, we have to decode it.
        #     # Get the data and decode it with base 64 decoder.
        #     parts = payload.get('parts')[0]
        #     data = parts['body']['data']
        #     data = data.replace("-","+").replace("_","/")
        #     decoded_data = base64.b64decode(data)

        #     # Now, the data obtained is in lxml. So, we will parse 
        #     # it with BeautifulSoup library
        #     soup = BeautifulSoup(decoded_data , "lxml")
        #     body = soup.body()

        #     # Printing the subject, sender's email and message
        #     print("Subject: ", subject)
        #     print("From: ", sender)
        #     print("Message: ", body)
        #     print('\n')
        #     break
        # except:
        #     print("cant print")
        #     pass




























def createDraft():
    """Create and insert a draft email.
    Print the returned draft's message and id.
    Returns: Draft object, including draft id and message meta data.

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
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
        # create gmail api client
        service = build("gmail", "v1", credentials=creds)

        message = EmailMessage()

        message.set_content("This is automated draft mail")

        message["To"] = "jparra2357@gmail.com"
        message["From"] = "jparra2357@gmail.com"
        message["Subject"] = "hola"

        # encoded message
        encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

        create_message = {"message": {"raw": encoded_message}}
        # pylint: disable=E1101
        draft = (
            service.users()
            .drafts()
            .create(userId="me", body=create_message)
            .execute()
        )

        print(f'Draft id: {draft["id"]}\nDraft message: {draft["message"]}')

    except HttpError as error:
        print(f"An error occurred: {error}")
        draft = None

    return draft


































def sendEmail():
    # Similar to createDraft() but with "send" api
    """Create and send an email message
    Print the returned  message id
    Returns: Message object, including message id

    Load pre-authorized user credentials from the environment.
    TODO(developer) - See https://developers.google.com/identity
    for guides on implementing OAuth2 for the application.
    """
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

        message.set_content("Mandando este mensaje desde gmail api")

        message["To"] = "jparra2357@gmail.com"
        message["From"] = "jparra2357@gmail.com"
        message["Subject"] = "Nuevo Correo"

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
        send_message = None
    return send_message




























def createEvent():
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

    event = {
        'summary': 'Sample event',
        # 'location': '800 Howard St., San Francisco, CA 94103',
        # 'description': 'A chance to hear more about Google\'s developer products.',
        'start': {
            'dateTime': '2025-12-28T09:00:00-07:00',
            'timeZone': 'America/New_York',
        },
        'end': {
            'dateTime': '2025-12-28T17:00:00-07:00',
            'timeZone': 'America/New_York',
        },
        # 'recurrence': [
        #     'RRULE:FREQ=DAILY;COUNT=2'
        # ],
        'attendees': [
            {'email': 'jparra2357@gmail.com'},
            # {'email': 'sbrin@example.com'},
        ],
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


    return





















def readEvent():
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
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        print("Getting the upcoming 10 events")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        # Prints the start and name of the next 10 events
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(start, event["summary"])

    except HttpError as error:
        print(f"An error occurred: {error}")


    return














def readEventsDate(day:str = None):
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
        service = build("calendar", "v3", credentials=creds)

        # Call the Calendar API
        # now = datetime.datetime.now(tz=datetime.timezone.utc).isoformat()
        minDay = datetime.datetime(2025, 12, 28, tzinfo=datetime.timezone.utc).isoformat()
        maxDay = datetime.datetime(2025, 12, 29, tzinfo=datetime.timezone.utc).isoformat()
        print("Getting the upcoming 10 events")
        events_result = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=minDay,
                timeMax=maxDay,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            print("No upcoming events found.")
            return

        # Prints the start and name of the next 10 events
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            print(start, event["summary"])

    except HttpError as error:
        print(f"An error occurred: {error}")


    return


















if __name__ == "__main__":
    # main()
    # getEmails()
    # createDraft()
    # sendEmail()
    # createEvent()
    # readEvent()
    readEventsDate()




















