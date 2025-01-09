import base64
import logging
import os.path
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these SCOPES, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    # 'https://www.googleapis.com/auth/gmail.readonly'
]


def create_message(sender, to, subject, message_text):
    """Create a message for an email."""
    message = MIMEText(message_text)
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}


def create_message_with_attachment(sender, to, subject, message_text, file_path):
    """Create a message with an attachment."""
    # Create the email container (multipart)
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    # Add the email body
    message.attach(MIMEText(message_text, 'plain'))

    # Process the file attachment
    file_name = os.path.basename(file_path)
    with open(file_path, 'rb') as file:
        file_content = MIMEBase('application', 'octet-stream')
        file_content.set_payload(file.read())
    encoders.encode_base64(file_content)
    file_content.add_header('Content-Disposition', f'attachment; filename="{file_name}"')
    message.attach(file_content)

    # Encode the message in base64 for the Gmail API
    return {'raw': base64.urlsafe_b64encode(message.as_bytes()).decode()}


def authenticate_gmail(token_path, credential_path):
    """Authenticate the user and return the Gmail service."""
    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credential_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'w') as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service


class GmailService:

    def __init__(self, token_path: str, credential_path: str):
        self.service = authenticate_gmail(token_path, credential_path)

    def send_email(self, sender, to, subject, message_text, file_path=None):
        """Send an email using the Gmail API. Supports attachments."""
        try:
            if file_path:
                message = create_message_with_attachment(sender, to, subject, message_text, file_path)
            else:
                message = create_message(sender, to, subject, message_text)
            sent_message = self.service.users().messages().send(userId="me", body=message).execute()
            print(f"Message sent! Message Id: {sent_message['id']}")
        except Exception as error:
            print(f"An error occurred: {error}")

    def get_emails(self, query='', max_results=10):
        try:
            # List messages based on the query
            service = self.service
            results = service.users().messages().list(userId='me', q=query, maxResults=max_results).execute()
            messages = results.get('messages', [])

            emails = []
            for message in messages:
                # Fetch the full message
                msg = service.users().messages().get(userId='me', id=message['id'], format='full').execute()

                # Extract message details
                payload = msg['payload']
                headers = payload['headers']
                subject = next(header['value'] for header in headers if header['name'] == 'Subject')
                sender = next(header['value'] for header in headers if header['name'] == 'From')

                # Decode the email body
                body = ''
                if 'parts' in payload:
                    for part in payload['parts']:
                        if part['mimeType'] == 'text/plain':
                            body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                            break
                elif 'body' in payload:
                    body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')

                emails.append({'subject': subject, 'sender': sender, 'body': body})

            return emails

        except Exception as error:
            logging.error(f"An error occurred: {error}")
            return []