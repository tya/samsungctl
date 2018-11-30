import base64
import json
import ssl
import os
import sys
import threading
import socket
import requests
from . import exceptions

import logging

logger = logging.getLogger('samsungctl')


URL_TEMPLATE = (
    "{protocol}://{host}:{port}/api/v2/channels"
    "/samsung.remote.control?name={name}{token}"
)

BUTTON_PRESS_TEMPLATE = dict(
    method='ms.remote.control',
    params=dict(
        Cmd='Click',
        DataOfCmd=None,
        Option='false',
        TypeOfRemote='SendRemoteKey'
    )
)

try:
    from websocket import WebSocketApp
except:
    class WebsocketApp(object):
        pass


def get_token_file():
    if sys.platform.startswith('win'):
        path = os.path.join(os.environ['APPDATA'], 'samsungctl')
    else:
        path = os.path.join(os.path.expandvars('~'), '.samsungctl')
    if not os.path.exists(path):
        os.mkdir(path)

    config_file = os.path.join(path, 'token.dat')
    if not os.path.exists(config_file):
        with open(config_file, 'w') as f:
            f.write('')

    return open(config_file, 'rw')


class RemoteWebsocket(WebSocketApp):
    """Object for remote control connection."""

    def on_open(self, ws):
        self._socket = ws

    def on_close(self, _):
        self._socket = None
        self._connect_event.clear()

    def on_error(self, _, err):
        logger.error('Websocket Error: %s', err)

    def on_message(self, _, message):
        response = json.loads(message)
        logger.debug('Incoming message: %s', message)

        if response['event'] == 'ms.channel.connect':
            if 'data' in response and 'token' in response['data']:
                self.tokens = (
                    self.config['device_id'] + ':' + response['data']['token']
                )

                logger.info("Websocket SSL Access granted.")
                self._authorization_event.set()

            else:
                logger.info("Websocket Access granted.")

            self._connect_event.set()

        if response['event'] == 'ms.channel.unauthorized':
            self._authorization_event.clear()
            self._connect_event.set()

        else:
            self._receive_event.set()

    def __init__(self, ip_address, port=None, device_id=None):
        if isinstance(ip_address, dict):
            self.config = ip_address
            self.config['device_id'] = self.config['host']
        else:
            self.config = dict(
                host=ip_address,
                port=port,
                name=socket.gethostname() + ':' + device_id,
                device_id=device_id
            )

        self.send = self.control
        self._token_file = get_token_file()
        self._connect_event = threading.Event()
        self._receive_event = threading.Event()
        self._authorization_event = threading.Event()
        self._send_lock = threading.Lock()
        self._socket = None
        self._run_thread = None
        self.run_forever()

    @property
    def tokens(self):
        tokens = self._token_file.read().split('\n')
        self._token_file.seek(0)
        return tokens

    @tokens.setter
    def tokens(self, value):
        token_name = value.split(':')[0]
        tokens = self.tokens

        for i, token in enumerate(tokens):
            if token.startswith(token_name):
                tokens[i] = value
                break
        else:
            tokens += [value]

        self._token_file.write('\n'.join(tokens))
        self._token_file.flush()
        self._token_file.seek(0)

    def run_forever(self):
        def do():

            if self.config['port'] == 8002:
                WebSocketApp.run_forever(
                    self,
                    sslopt=dict(cert_reqs=ssl.CERT_NONE)
                )
            else:
                WebSocketApp.run_forever(self)

            self._run_thread = None

        if self._run_thread is None:
            self._connect_event.clear()
            self._receive_event.clear()

            tokens = self.tokens

            for token in tokens:
                if token.startswith(self.config['device_id']):
                    self.config['token'] = '&token=' + token.split(':', 1)[-1]
                    self.config['protocol'] = 'wss'
                    self.config['port'] = 8002
                    self._authorization_event.set()
                    break
            else:
                url = 'http://{0}:8001/api/v2'.format(self.config['host'])
                response = requests.get(url)
                try:
                    response = json.loads(response.content)
                    if (
                        'device' in response and
                        'TokenAuthSupport' in response['device'] and
                        response['device']['TokenAuthSupport']
                    ):
                        self.config['protocol'] = 'wss'
                        self.config['port'] = 8002
                        self.config['token'] = ''

                    else:
                        raise ValueError

                except ValueError:
                    self.config['protocol'] = 'ws'
                    self.config['port'] = 8001
                    self.config['token'] = ''
                    self._authorization_event.set()

            self.config['name'] = (
                self._serialize_string(self.config["name"])
            )

            url = URL_TEMPLATE.format(**self.config)

            super(RemoteWebsocket, self).__init__(url)

            self._run_thread = threading.Thread(target=do)
            self._run_thread.start()
            self._connect_event.wait(5)
            self._authorization_event.wait(30)

            if not self._authorization_event.isSet():
                raise RuntimeError('Websocket Authentication Error')

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        """Close the connection."""
        logger.debug("Closing Websocket Connection.")
        self.close()
        self._token_file.close()

    def control(self, key):
        """Send a control command."""
        if self._socket is None:
            raise exceptions.ConnectionClosed()

        with self._send_lock:
            self._receive_event.clear()
            BUTTON_PRESS_TEMPLATE['params']['DataOfCmd'] = key
            payload = json.dumps(BUTTON_PRESS_TEMPLATE)
            logger.info("Sending control command: %s", key)
            logger.debug("Command data: %s", payload)

            WebSocketApp.send(self, payload)

            self._receive_event.wait(self._key_interval)

    _key_interval = 0.5

    @staticmethod
    def _serialize_string(string):
        if isinstance(string, str):
            string = str.encode(string)
        return base64.b64encode(string).decode("utf-8")
