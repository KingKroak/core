import os

import pandas as pd

from utils.gmail import GmailService

if __name__ == '__main__':
    print(os.getcwd())

    df = pd.DataFrame()

    text = f'<b>hello world</b>'
    text += df.to_html()

    gmail_service = GmailService(f'../utils/token.json', f'../utils/credentials.json')
    gmail_service.send_email(
        'AtraxaBot',
        'atraxa.investments@gmail.com',
        'Hello World!',
        text,
        message_format='html'
    )
