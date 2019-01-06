# -*- coding: utf-8 -*-
from __future__ import print_function
import threading
import unittest
import socket
import sys
import ssl
import base64
import json
import random
import string
import time
import uuid
import samsungctl
from . import responses
from . import SimpleWebSocketServer

import logging

logger = logging.getLogger('samsungctl')
logger.setLevel(logging.DEBUG)


class URL(str):

    def __init__(self, value):
        self.value = value
        str.__init__(self, value)

    def __radd__(self, other):
        print('ADDING to URL:' + str(other))
        return self.value


class URL_FORMAT(object):
    def format(self, host, port, _):
        print('formatting URL: ' + host + ':' + str(port))
        return URL("ws://{}:{}".format(host, port))


class SSL_URL_FORMAT(object):

    def format(self, host, port, _):
        print('formatting SSL_URL: ' + host + ':' + str(port))
        return URL("wss://{}:{}".format(host, port))


sys.modules['samsungctl.remote_websocket'].URL_FORMAT = URL_FORMAT()
sys.modules['samsungctl.remote_websocket'].SSL_URL_FORMAT = SSL_URL_FORMAT()

logger.setLevel(logging.INFO)

TOKEN = ''.join(
    random.choice(string.digits + string.ascii_letters) for _ in range(20)
)


APP_NAMES = list(
    app['name'] for app in responses.INSTALLED_APP_RESPONSE['data']
)
APP_IDS = list(
    app['appId'] for app in responses.INSTALLED_APP_RESPONSE['data']
)

APP_NAMES += list(
    app['name'] for app in responses.EDEN_APP_RESPONSE['data']['data']
    if app['name'] not in APP_NAMES
)
APP_IDS += list(
    app['id'] for app in responses.EDEN_APP_RESPONSE['data']['data']
    if app['id'] not in APP_IDS
)


def key_wrapper(func):
    key = func.__name__.split('_', 2)[-1]

    def wrapper(self):
        if self._remote is None:
            self.skipTest('no connection')

        self.set_key_message('Click', key)
        self._remote.command(key)
        self._key_event.wait(3)

        if not self._key_event.isSet():
            self.skipTest('timed out')

    return wrapper


class WebSocketClass(SimpleWebSocketServer.WebSocket):

    def send(self, data):
        if not isinstance(data, str):
            payload = json.dumps(data)
        else:
            payload = data
        self.sendMessage(payload)

    def handleMessage(self):
        self.server.on_message(self, self.data)

    def handleConnected(self):
        self.server.on_connect(self)

    def handleClose(self):
        self.server.on_disconnect(self)


original_decorateSocket = SimpleWebSocketServer.SimpleWebSocketServer._decorateSocket
original_constructWebSocket = SimpleWebSocketServer.SimpleWebSocketServer._constructWebSocket


def _decorateSocket(self, sock):
    return ssl.wrap_socket(sock, server_side=True)


def _constructWebSocket(self, sock, address):
    ws = self.websocketclass(self, sock, address)
    ws.usingssl = True
    return ws


class Server(object):

    def __init__(self, host, port, use_ssl):
        if use_ssl:
            SimpleWebSocketServer.SimpleWebSocketServer._decorateSocket = _decorateSocket
            SimpleWebSocketServer.SimpleWebSocketServer._constructWebSocket = _constructWebSocket
        else:
            SimpleWebSocketServer.SimpleWebSocketServer._decorateSocket = original_decorateSocket
            SimpleWebSocketServer.SimpleWebSocketServer._constructWebSocket = original_constructWebSocket

        self._ws = SimpleWebSocketServer.SimpleWebSocketServer(host, port, WebSocketClass)

        self._ws.on_message = self.on_message
        self._ws.on_message = self.on_connect
        self._ws.on_disconnect = self.on_disconnect

        self._on_message = None
        self._on_connect = None
        self._on_disconnect = None
        self._client = None

    def __setattr__(self, key, value):
        if key in ('on_message', 'on_connect', 'on_disconnect'):
            object.__setattr__(self, '_' + key, value)
        else:
            object.__setattr__(self, key, value)

    def send(self, message):
        if self._client is not None:
            self._client.send(message)

    def close(self):
        self._ws.close()

    def on_message(self, *args):
        print('Base on message')

        if self._on_message is not None:
            self._on_message(*args)

    def on_connect(self, client):
        print('Base on connection')
        self._client = client
        if self._on_connect is not None:
            self._on_connect(client)

    def on_disconnect(self, *args):
        print('Base on disconnection')

        self._client = None
        if self._on_disconnect is not None:
            self._on_disconnect(*args)

    def serveforever(self, startup_event, err):
        startup_event.set()
        try:
            self._ws.serveforever()
        except Exception as e:
            err[0] = e


class TestBase(object):
    _server = None
    _remote = None
    _key_event = threading.Event()
    _thread = None
    config = None
    client = None
    _startup_event = threading.Event()
    _connection_event = threading.Event()

    @staticmethod
    def _unserialize_string(s):
        return base64.b64decode(s).encode("utf-8")

    @staticmethod
    def _serialize_string(s):
        return base64.b64encode(s).decode("utf-8")

    def set_key_message(self, cmd, key):
        raise NotImplementedError

    def on_connect(self, client):
        raise NotImplementedError

    def test_001_CONNECTION(self):
        logger.info('starting tests')
        self._startup_event.clear()
        self._connection_event.clear()
        err = [None]

        self._server.on_disconnect = self.on_disconnect

        self._thread = threading.Thread(
            target=self._server.serveforever,
            args=(self._startup_event, err)
        )
        self._thread.daemon = True
        self._thread.start()
        self._startup_event.wait()
        self._startup_event.clear()
        self._startup_event.wait(5.0)

        def do():
            logger.info('connection test')
            logger.info(str(self.config))
            self._remote = samsungctl.Remote(self.config).__enter__()

        threading.Thread(target=do).start()
        self._connection_event.wait(10.0)
        if not self._connection_event.isSet():
            if err[0] is not None:
                raise err[0]
            self.fail('timed out')

    @key_wrapper
    def test_0100_KEY_POWEROFF(self):
        """Power OFF key test"""
        pass

    @key_wrapper
    def test_0101_KEY_POWERON(self):
        """Power On key test"""
        pass

    @key_wrapper
    def test_0102_KEY_POWER(self):
        """Power Toggle key test"""
        pass

    @key_wrapper
    def test_0103_KEY_SOURCE(self):
        """Source key test"""
        pass

    @key_wrapper
    def test_0104_KEY_COMPONENT1(self):
        """Component 1 key test"""
        pass

    @key_wrapper
    def test_0105_KEY_COMPONENT2(self):
        """Component 2 key test"""
        pass

    @key_wrapper
    def test_0106_KEY_AV1(self):
        """AV 1 key test"""
        pass

    @key_wrapper
    def test_0107_KEY_AV2(self):
        """AV 2 key test"""
        pass

    @key_wrapper
    def test_0108_KEY_AV3(self):
        """AV 3 key test"""
        pass

    @key_wrapper
    def test_0109_KEY_SVIDEO1(self):
        """S Video 1 key test"""
        pass

    @key_wrapper
    def test_0110_KEY_SVIDEO2(self):
        """S Video 2 key test"""
        pass

    @key_wrapper
    def test_0111_KEY_SVIDEO3(self):
        """S Video 3 key test"""
        pass

    @key_wrapper
    def test_0112_KEY_HDMI(self):
        """HDMI key test"""
        pass

    @key_wrapper
    def test_0113_KEY_HDMI1(self):
        """HDMI 1 key test"""
        pass

    @key_wrapper
    def test_0114_KEY_HDMI2(self):
        """HDMI 2 key test"""
        pass

    @key_wrapper
    def test_0115_KEY_HDMI3(self):
        """HDMI 3 key test"""
        pass

    @key_wrapper
    def test_0116_KEY_HDMI4(self):
        """HDMI 4 key test"""
        pass

    @key_wrapper
    def test_0117_KEY_FM_RADIO(self):
        """FM Radio key test"""
        pass

    @key_wrapper
    def test_0118_KEY_DVI(self):
        """DVI key test"""
        pass

    @key_wrapper
    def test_0119_KEY_DVR(self):
        """DVR key test"""
        pass

    @key_wrapper
    def test_0120_KEY_TV(self):
        """TV key test"""
        pass

    @key_wrapper
    def test_0121_KEY_ANTENA(self):
        """Analog TV key test"""
        pass

    @key_wrapper
    def test_0122_KEY_DTV(self):
        """Digital TV key test"""
        pass

    @key_wrapper
    def test_0123_KEY_1(self):
        """Key1 key test"""
        pass

    @key_wrapper
    def test_0124_KEY_2(self):
        """Key2 key test"""
        pass

    @key_wrapper
    def test_0125_KEY_3(self):
        """Key3 key test"""
        pass

    @key_wrapper
    def test_0126_KEY_4(self):
        """Key4 key test"""
        pass

    @key_wrapper
    def test_0127_KEY_5(self):
        """Key5 key test"""
        pass

    @key_wrapper
    def test_0128_KEY_6(self):
        """Key6 key test"""
        pass

    @key_wrapper
    def test_0129_KEY_7(self):
        """Key7 key test"""
        pass

    @key_wrapper
    def test_0130_KEY_8(self):
        """Key8 key test"""
        pass

    @key_wrapper
    def test_0131_KEY_9(self):
        """Key9 key test"""
        pass

    @key_wrapper
    def test_0132_KEY_0(self):
        """Key0 key test"""
        pass

    @key_wrapper
    def test_0133_KEY_PANNEL_CHDOWN(self):
        """3D key test"""
        pass

    @key_wrapper
    def test_0134_KEY_ANYNET(self):
        """AnyNet+ key test"""
        pass

    @key_wrapper
    def test_0135_KEY_ESAVING(self):
        """Energy Saving key test"""
        pass

    @key_wrapper
    def test_0136_KEY_SLEEP(self):
        """Sleep Timer key test"""
        pass

    @key_wrapper
    def test_0137_KEY_DTV_SIGNAL(self):
        """DTV Signal key test"""
        pass

    @key_wrapper
    def test_0138_KEY_CHUP(self):
        """Channel Up key test"""
        pass

    @key_wrapper
    def test_0139_KEY_CHDOWN(self):
        """Channel Down key test"""
        pass

    @key_wrapper
    def test_0140_KEY_PRECH(self):
        """Previous Channel key test"""
        pass

    @key_wrapper
    def test_0141_KEY_FAVCH(self):
        """Favorite Channels key test"""
        pass

    @key_wrapper
    def test_0142_KEY_CH_LIST(self):
        """Channel List key test"""
        pass

    @key_wrapper
    def test_0143_KEY_AUTO_PROGRAM(self):
        """Auto Program key test"""
        pass

    @key_wrapper
    def test_0144_KEY_MAGIC_CHANNEL(self):
        """Magic Channel key test"""
        pass

    @key_wrapper
    def test_0145_KEY_VOLUP(self):
        """Volume Up key test"""
        pass

    @key_wrapper
    def test_0146_KEY_VOLDOWN(self):
        """Volume Down key test"""
        pass

    @key_wrapper
    def test_0147_KEY_MUTE(self):
        """Mute key test"""
        pass

    @key_wrapper
    def test_0148_KEY_UP(self):
        """Navigation Up key test"""
        pass

    @key_wrapper
    def test_0149_KEY_DOWN(self):
        """Navigation Down key test"""
        pass

    @key_wrapper
    def test_0150_KEY_LEFT(self):
        """Navigation Left key test"""
        pass

    @key_wrapper
    def test_0151_KEY_RIGHT(self):
        """Navigation Right key test"""
        pass

    @key_wrapper
    def test_0152_KEY_RETURN(self):
        """Navigation Return/Back key test"""
        pass

    @key_wrapper
    def test_0153_KEY_ENTER(self):
        """Navigation Enter key test"""
        pass

    @key_wrapper
    def test_0154_KEY_REWIND(self):
        """Rewind key test"""
        pass

    @key_wrapper
    def test_0155_KEY_STOP(self):
        """Stop key test"""
        pass

    @key_wrapper
    def test_0156_KEY_PLAY(self):
        """Play key test"""
        pass

    @key_wrapper
    def test_0157_KEY_FF(self):
        """Fast Forward key test"""
        pass

    @key_wrapper
    def test_0158_KEY_REC(self):
        """Record key test"""
        pass

    @key_wrapper
    def test_0159_KEY_PAUSE(self):
        """Pause key test"""
        pass

    @key_wrapper
    def test_0160_KEY_LIVE(self):
        """Live key test"""
        pass

    @key_wrapper
    def test_0161_KEY_QUICK_REPLAY(self):
        """fnKEY_QUICK_REPLAY key test"""
        pass

    @key_wrapper
    def test_0162_KEY_STILL_PICTURE(self):
        """fnKEY_STILL_PICTURE key test"""
        pass

    @key_wrapper
    def test_0163_KEY_INSTANT_REPLAY(self):
        """fnKEY_INSTANT_REPLAY key test"""
        pass

    @key_wrapper
    def test_0164_KEY_PIP_ONOFF(self):
        """PIP On/Off key test"""
        pass

    @key_wrapper
    def test_0165_KEY_PIP_SWAP(self):
        """PIP Swap key test"""
        pass

    @key_wrapper
    def test_0166_KEY_PIP_SIZE(self):
        """PIP Size key test"""
        pass

    @key_wrapper
    def test_0167_KEY_PIP_CHUP(self):
        """PIP Channel Up key test"""
        pass

    @key_wrapper
    def test_0168_KEY_PIP_CHDOWN(self):
        """PIP Channel Down key test"""
        pass

    @key_wrapper
    def test_0169_KEY_AUTO_ARC_PIP_SMALL(self):
        """PIP Small key test"""
        pass

    @key_wrapper
    def test_0170_KEY_AUTO_ARC_PIP_WIDE(self):
        """PIP Wide key test"""
        pass

    @key_wrapper
    def test_0171_KEY_AUTO_ARC_PIP_RIGHT_BOTTOM(self):
        """PIP Bottom Right key test"""
        pass

    @key_wrapper
    def test_0172_KEY_AUTO_ARC_PIP_SOURCE_CHANGE(self):
        """PIP Source Change key test"""
        pass

    @key_wrapper
    def test_0173_KEY_PIP_SCAN(self):
        """PIP Scan key test"""
        pass

    @key_wrapper
    def test_0174_KEY_VCR_MODE(self):
        """VCR Mode key test"""
        pass

    @key_wrapper
    def test_0175_KEY_CATV_MODE(self):
        """CATV Mode key test"""
        pass

    @key_wrapper
    def test_0176_KEY_DSS_MODE(self):
        """DSS Mode key test"""
        pass

    @key_wrapper
    def test_0177_KEY_TV_MODE(self):
        """TV Mode key test"""
        pass

    @key_wrapper
    def test_0178_KEY_DVD_MODE(self):
        """DVD Mode key test"""
        pass

    @key_wrapper
    def test_0179_KEY_STB_MODE(self):
        """STB Mode key test"""
        pass

    @key_wrapper
    def test_0180_KEY_PCMODE(self):
        """PC Mode key test"""
        pass

    @key_wrapper
    def test_0181_KEY_GREEN(self):
        """Green key test"""
        pass

    @key_wrapper
    def test_0182_KEY_YELLOW(self):
        """Yellow key test"""
        pass

    @key_wrapper
    def test_0183_KEY_CYAN(self):
        """Cyan key test"""
        pass

    @key_wrapper
    def test_0184_KEY_RED(self):
        """Red key test"""
        pass

    @key_wrapper
    def test_0185_KEY_TTX_MIX(self):
        """Teletext Mix key test"""
        pass

    @key_wrapper
    def test_0186_KEY_TTX_SUBFACE(self):
        """Teletext Subface key test"""
        pass

    @key_wrapper
    def test_0187_KEY_ASPECT(self):
        """Aspect Ratio key test"""
        pass

    @key_wrapper
    def test_0188_KEY_PICTURE_SIZE(self):
        """Picture Size key test"""
        pass

    @key_wrapper
    def test_0189_KEY_4_3(self):
        """Aspect Ratio 4:3 key test"""
        pass

    @key_wrapper
    def test_0190_KEY_16_9(self):
        """Aspect Ratio 16:9 key test"""
        pass

    @key_wrapper
    def test_0191_KEY_EXT14(self):
        """Aspect Ratio 3:4 (Alt) key test"""
        pass

    @key_wrapper
    def test_0192_KEY_EXT15(self):
        """Aspect Ratio 16:9 (Alt) key test"""
        pass

    @key_wrapper
    def test_0193_KEY_PMODE(self):
        """Picture Mode key test"""
        pass

    @key_wrapper
    def test_0194_KEY_PANORAMA(self):
        """Picture Mode Panorama key test"""
        pass

    @key_wrapper
    def test_0195_KEY_DYNAMIC(self):
        """Picture Mode Dynamic key test"""
        pass

    @key_wrapper
    def test_0196_KEY_STANDARD(self):
        """Picture Mode Standard key test"""
        pass

    @key_wrapper
    def test_0197_KEY_MOVIE1(self):
        """Picture Mode Movie key test"""
        pass

    @key_wrapper
    def test_0198_KEY_GAME(self):
        """Picture Mode Game key test"""
        pass

    @key_wrapper
    def test_0199_KEY_CUSTOM(self):
        """Picture Mode Custom key test"""
        pass

    @key_wrapper
    def test_0200_KEY_EXT9(self):
        """Picture Mode Movie (Alt) key test"""
        pass

    @key_wrapper
    def test_0201_KEY_EXT10(self):
        """Picture Mode Standard (Alt) key test"""
        pass

    @key_wrapper
    def test_0202_KEY_MENU(self):
        """Menu key test"""
        pass

    @key_wrapper
    def test_0203_KEY_TOPMENU(self):
        """Top Menu key test"""
        pass

    @key_wrapper
    def test_0204_KEY_TOOLS(self):
        """Tools key test"""
        pass

    @key_wrapper
    def test_0205_KEY_HOME(self):
        """Home key test"""
        pass

    @key_wrapper
    def test_0206_KEY_CONTENTS(self):
        """Contents key test"""
        pass

    @key_wrapper
    def test_0207_KEY_GUIDE(self):
        """Guide key test"""
        pass

    @key_wrapper
    def test_0208_KEY_DISC_MENU(self):
        """Disc Menu key test"""
        pass

    @key_wrapper
    def test_0209_KEY_DVR_MENU(self):
        """DVR Menu key test"""
        pass

    @key_wrapper
    def test_0210_KEY_HELP(self):
        """Help key test"""
        pass

    @key_wrapper
    def test_0211_KEY_INFO(self):
        """Info key test"""
        pass

    @key_wrapper
    def test_0212_KEY_CAPTION(self):
        """Caption key test"""
        pass

    @key_wrapper
    def test_0213_KEY_CLOCK_DISPLAY(self):
        """ClockDisplay key test"""
        pass

    @key_wrapper
    def test_0214_KEY_SETUP_CLOCK_TIMER(self):
        """Setup Clock key test"""
        pass

    @key_wrapper
    def test_0215_KEY_SUB_TITLE(self):
        """Subtitle key test"""
        pass

    @key_wrapper
    def test_0216_KEY_ZOOM_MOVE(self):
        """Zoom Move key test"""
        pass

    @key_wrapper
    def test_0217_KEY_ZOOM_IN(self):
        """Zoom In key test"""
        pass

    @key_wrapper
    def test_0218_KEY_ZOOM_OUT(self):
        """Zoom Out key test"""
        pass

    @key_wrapper
    def test_0219_KEY_ZOOM1(self):
        """Zoom 1 key test"""
        pass

    @key_wrapper
    def test_0220_KEY_ZOOM2(self):
        """Zoom 2 key test"""
        pass

    def test_0221_KEY_BT_VOICE_ON(self):
        self.skipTest('not used')

    def test_0222_KEY_BT_VOICE_OFF(self):
        self.skipTest('not used')

    def on_disconnect(self, c):
        print('disconnected: ' + str(c.address))
        self.client = None

    @classmethod
    def tearDownClass(cls):
        cls._server.close()
        cls._server = None


class WebsocketTest(TestBase, unittest.TestCase):
    ssl = False
    _applications = None

    def test_0221_KEY_BT_VOICE_ON(self):
        if self._remote is None:
            self.skipTest('no connection')

        def on_message(client, message):
            expected_message = dict(
                Cmd='Press',
                DataOfCmd='KEY_BT_VOICE',
                Option="false",
                TypeOfRemote="SendRemoteKey"
            )

            message = json.loads(message)
            self.assertEqual(expected_message, message)
            payload = dict(event="ms.voiceApp.standby")
            client.send(json.dumps(payload))
            self._key_event.set()

        self._key_event.clear()
        self._server.on_message = on_message
        self._remote.start_voice_recognition()

        self._key_event.wait(3)
        if not self._key_event.isSet():
            self.skipTest('timed out')

    def test_0222_KEY_BT_VOICE_OFF(self):
        if self._remote is None:
            self.skipTest('no connection')

        def on_message(client, message):
            expected_message = dict(
                Cmd='Release',
                DataOfCmd='KEY_BT_VOICE',
                Option="false",
                TypeOfRemote="SendRemoteKey"
            )
            message = json.loads(message)

            self.assertEqual(expected_message, message)
            payload = dict(event="ms.voiceApp.hide")
            client.send(json.dumps(payload))

            self._key_event.set()

        self._key_event.clear()
        self._server.on_message = on_message
        self._remote.stop_voice_recognition()

        self._key_event.wait(3)
        if not self._key_event.isSet():
            self.skipTest('timed out')

    def test_0300_EDEN_APP_GET(self):
        if self._remote is None:
            self.skipTest('no connection')

        def on_message(client, message):
            eden_message = dict(
                method='ms.channel.emit',
                params=dict(
                    data='',
                    event='ed.edenApp.get',
                    to='host'
                )
            )
            installed_message = dict(
                method='ms.channel.emit',
                params=dict(
                    data='',
                    event='ed.installedApp.get',
                    to='host'
                )
            )

            message = json.loads(message)

            if message == eden_message:
                self.assertEqual(eden_message, message)
                client.send(json.dumps(responses.EDEN_APP_RESPONSE))
                eden_event.set()
            else:
                self.assertEqual(installed_message, message)
                client.send(json.dumps(responses.INSTALLED_APP_RESPONSE))
                installed_event.set()

        eden_event = threading.Event()
        installed_event = threading.Event()
        self._server.on_message = on_message

        def do():
            self._applications = self._remote.applications
        t = threading.Thread(target=do)
        t.daemon = True
        t.start()

        eden_event.wait(2.0)
        installed_event.wait(2.0)

        if not eden_event.isSet() or not installed_event.isSet():
            self.skipTest('timed out')

        elif self._applications is None:
            self.skipTest('no applications received')

    def test_0301_CHECK_APPLICATION_NAMES(self):
        if self._remote is None:
            self.skipTest('no connection')

        if self._applications is None:
            self.skipTest('previous test failed')
        else:
            app_names = APP_NAMES[:]
            unknown_names = []

            for app in self._applications:
                if app.name in app_names:
                    app_names.remove(app.name)
                else:
                    unknown_names += [[app.name, app.id]]

            if unknown_names:
                self.skipTest('unknown apps: ' + str(unknown_names))

            if app_names:
                self.skipTest('unused apps: ' + str(app_names))

    def test_0302_CHECK_APPLICATION_IDS(self):
        if self._remote is None:
            self.skipTest('no connection')

        if self._applications is None:
            self.skipTest('previous test failed')
        else:
            app_ids = APP_IDS[:]
            unknown_ids = []

            for app in self._applications:
                if app.id in app_ids:
                    app_ids.remove(app.id)
                else:
                    unknown_ids += [[app.name, app.id]]

            if unknown_ids:
                self.skipTest('unknown apps: ' + str(unknown_ids))

            if app_ids:
                self.skipTest('unused apps: ' + str(app_ids))

    def set_key_message(self, cmd, key):
        self._key_event.clear()
        expected_message = dict(
            Cmd=cmd,
            DataOfCmd=key,
            Option="false",
            TypeOfRemote="SendRemoteKey"
        )

        def on_message(_, message):
            message = json.loads(message)
            self.assertEqual(expected_message, message)
            self._key_event.set()

        self._server.on_message = on_message

    @classmethod
    def setUpClass(cls):
        print(cls._server)
        cls._startup_event.clear()
        cls.client = None
        host = socket.gethostbyname(socket.gethostname())
        cls.config = dict(
            name="samsungctl",
            description="PC",
            id="",
            method="websocket",
            host=host,
            port=8001,
            timeout=0
        )

        cls._server = Server(host, 8001, use_ssl=False)

        def on_connect(client):
            print('connected ' + str(client.address))
            cls.client = client

        cls._server.on_connect = on_connect

        def on_message(c, msg):
            print(msg)
            guid = str(uuid.uuid4())[1:-1]
            name = cls._serialize_string(cls.config['name'])

            clients = dict(
                attributes=dict(name=name),
                connectTime=time.time(),
                deviceName=name,
                id=guid,
                isHost=False
            )

            data = dict(clients=[clients], id=guid)
            payload = dict(data=data, event='ms.channel.connect')
            c.send(json.dumps(payload))
            cls._connection_event.set()

        cls._server.on_message = on_message

    def on_connect(self, client):
        print('connected')
        self.client = client

#
# class WebSocketSSLTest(WebsocketTest):
#     ssl = True
#
#     @classmethod
#     def setUpClass(cls):
#         print(cls._server)
#
#         cls._startup_event.clear()
#         host = socket.gethostbyname(socket.gethostname())
#         cls.client = None
#         cls.config = dict(
#             name="samsungctl",
#             description="PC",
#             id="",
#             method="websocket",
#             host=host,
#             port=8002,
#             timeout=0
#         )
#
#         cls._server = Server(host, 8002, use_ssl=True)
#
#         def on_connect(client):
#             print('connected ' + str(client.address))
#             cls.client = client
#
#         cls._server.on_connect = on_connect
#
#         def on_message(c, msg):
#             guid = str(uuid.uuid4())[1:-1]
#             name = cls._serialize_string(cls.config['name'])
#
#             clients = dict(
#                 attributes=dict(name=name, token=TOKEN),
#                 connectTime=time.time(),
#                 deviceName=name,
#                 id=guid,
#                 isHost=False
#             )
#
#             data = dict(clients=[clients], id=guid, token=TOKEN)
#             payload = dict(data=data, event='ms.channel.connect')
#             c.send(json.dumps(payload))
#
#             cls._connection_event.set()
#
#         cls._server.on_message = on_message
#
#     def on_connect(self, client):
#         print('connected')
#         self.client = client

#
# class LegacyTest(TestBase):
#
#     @classmethod
#     def setUpClass(self):
#         self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#         self.sock.Bind(('127.0.0.1', 55000))
#         self.sock.listen(1)
#
#         websocket_server.WebsocketServer(
#             port=8002,
#             host='127.0.0.1',
#             loglevel=logging.DEBUG
#         )
#
#     @classmethod
#     def tearDownClass(self):
#         pass


if __name__ == '__main__':
    sys.argv.append('-v')
    unittest.main()
