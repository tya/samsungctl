import base64
import socket
import struct
import threading

from . import exceptions

import logging

logger = logging.getLogger('samsungctl')


class RemoteLegacy(object):
    """Object for remote control connection."""

    def __init__(self, ip_address, device_id=None):
        """Make a new connection."""

        if isinstance(ip_address, dict):
            config = ip_address
        else:
            config = dict(
                host=ip_address,
                port=55000,
                description=socket.gethostname(),
                id=device_id,
                name=socket.gethostname() + ':' + device_id
            )

        self.send = self.control

        self._connect_event = threading.Event()
        self._receive_event = threading.Event()
        self._send_lock = threading.Lock()

        self.connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connection.connect((config["host"], config["port"]))

        payload = (
            b'\x64\x00' +
            self._serialize_string(config["description"]) +
            self._serialize_string(config["id"]) +
            self._serialize_string(config["name"])
        )

        packet = (
            b'\x00\x00\x00' +
            self._serialize_string(payload, True)
        )

        logger.info("Sending handshake.")

        self.connection.send(packet)
        self._read_response(True)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        """Close the connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.debug("Connection closed.")

    def control(self, key):
        """Send a control command."""
        if not self.connection:
            raise exceptions.ConnectionClosed()

        with self._send_lock:
            self._receive_event.clear()

            payload = (
                b'\x00\x00\x00' +
                self._serialize_string(key)
            )
            packet = (
                b'\x00\x00\x00' +
                self._serialize_string(payload, True)
            )

            logging.info("Sending control command: %s", key)
            self.connection.send(packet)
            self._read_response()
            self._receive_event.wait(self._key_interval)

    _key_interval = 0.2

    def _read_response(self, first_time=False):
        header = self.connection.recv(3)
        tv_name_len = struct.unpack("<H", header[1:3])[0]

        tv_name = self.connection.recv(tv_name_len)
        if first_time:
            logger.debug("Connected to '%s'.", tv_name.decode())

        response_len = struct.unpack("<H", self.connection.recv(2))[0]

        response = self.connection.recv(response_len)

        if len(response) == 0:
            self.close()
            raise exceptions.ConnectionClosed()

        if response == b'\x64\x00\x01\x00':
            logger.debug("Access granted.")
            return
        elif response == b'\x64\x00\x00\x00':
            raise exceptions.AccessDenied()
        elif response[0:1] == b'\x0A':
            if first_time:
                logger.warning("Waiting for authorization...")
            return self._read_response()
        elif response[0:1] == b'\x65':
            logger.warning("Authorization cancelled.")
            raise exceptions.AccessDenied()
        elif response == b'\x00\x00\x00\x00':
            logger.debug("Control accepted.")
            self._receive_event.set()
            return

        raise exceptions.UnhandledResponse(response)

    @staticmethod
    def _serialize_string(string, raw=False):
        if isinstance(string, str):
            string = string.encode('utf-8')

        if not raw:
            string = base64.b64encode(string)

        return bytes([len(string)]) + b"\x00" + string
