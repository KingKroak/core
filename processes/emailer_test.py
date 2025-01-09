import os

from utils.gmail import GmailService

if __name__ == '__main__':
    print(os.getcwd())
    gmail_service = GmailService(f'{os.getcwd()}/utils/token.json', f'{os.getcwd()}/utils/credentials.json')
    gmail_service.send_email(
        'AtraxaBot',
        'atraxa.investments@gmail.com',
        'Hello World!',
        'This is a test of the Gmail service component',
    )
