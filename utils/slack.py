import logging

import slack_sdk.errors
from slack_sdk import WebClient

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Alerter:

    def __init__(self, msg_source: str):
        self._msg_source = msg_source

    def error(self, message, channel=None):
        raise NotImplementedError

    def warning(self, message, channel=None):
        raise NotImplementedError

    def info(self, massage, channel=None):
        raise NotImplementedError

class LoggingAlerter(Alerter):

    def warning(self, message, channel=None):
        logging.warning('*{}*: *{}*"'.format(self._msg_source, message))

    def info(self, message, channel=None):
        logging.info('{}: {}"'.format(self._msg_source, message))

    def error(self, message, channel=None):
        logging.error('[ERROR] *{}*: *{}*'.format(self._msg_source, message))


class SlackAlerter(Alerter):

    def __init__(self,
                 msg_source: str,
                 default_slack_channel='alerts',
                 token='xoxb-8080144237524-8090333375121-3Ec2SagZ4kqs1ac7RtgwduUY'):
        super().__init__(msg_source)
        self.default_slack_channel = default_slack_channel
        self.web_client = WebClient(token=token)

    def _post(self, formatted_msg: str, channel=None):
        try:
            if channel is None:
                channel = self.default_slack_channel
            self.web_client.chat_postMessage(channel=channel, text=formatted_msg)
        except slack_sdk.errors.SlackApiError as e:
            logging.info(f'Failed to send message: {formatted_msg}')

    def error(self, message, channel=None):
        self._post('🚨 *{}: {}*'.format(self._msg_source, message))

    def warning(self, message, channel=None):
        self._post('*{}*: *{}*'.format(self._msg_source, message))

    def info(self, message, channel=None):
        self._post('{}: {}'.format(self._msg_source, message))

