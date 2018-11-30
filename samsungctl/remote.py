
from .upnp.discover import discover
from . import exceptions
from .remote_legacy import RemoteLegacy
from .remote_websocket import RemoteWebsocket

import logging

logger = logging.getLogger('samsungctl')


class Remote(object):
    LOG_OFF = logging.NOTSET
    LOG_CRITICAL = logging.CRITICAL
    LOG_ERROR = logging.ERROR
    LOG_WARNING = logging.WARNING
    LOG_INFO = logging.INFO
    LOG_DEBUG = logging.DEBUG

    def __init__(self, ip_address=None, device_id=None, log_level=None):
        if log_level is not None:
            logger.setLevel(log_level)

        config = ip_address

        if isinstance(ip_address, dict):
            ip_address = ip_address['host']

        for device in discover(8):
            if ip_address is None and device_id is None:
                break
            if ip_address is not None and device.ip_address == ip_address:
                break
            if device_id is not None and device.device_id == device_id:
                break

        else:
            if isinstance(config, dict):
                if config['method'] == 'legacy':
                    device = RemoteLegacy(config)
                else:
                    device = RemoteWebsocket(config)
            else:
                raise RuntimeError('Unable to locate TV')

        self._device = device

    def __enter__(self):
        return self._device.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._device.__exit__(exc_type, exc_val, exc_tb)

    def close(self):
        return self._device.close()

    def control(self, key):
        return self._device.control(key)

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        return getattr(self.device, item)

    def __setattr__(self, key, value):
        if key == 'device':
            object.__setattr__(self, key, value)

        else:
            setattr(self._device, key, value)


