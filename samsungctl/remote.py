

import logging
import threading

from .remote_legacy import RemoteLegacy
from .remote_websocket import RemoteWebsocket
from .upnp import discover

logger = logging.getLogger('samsungctl')


class Remote(object):
    LOG_OFF = logging.NOTSET
    LOG_CRITICAL = logging.CRITICAL
    LOG_ERROR = logging.ERROR
    LOG_WARNING = logging.WARNING
    LOG_INFO = logging.INFO
    LOG_DEBUG = logging.DEBUG

    def __init__(self, ip_address=None, log_level=None):
        self._discovering = threading.Event()
        if log_level is not None:
            logger.setLevel(log_level)

        config = ip_address

        if isinstance(ip_address, dict):
            ip_address = ip_address['host']

        if ip_address is None:
            ip_address = '0.0.0.0'

        self._remote = None
        self.upnp_tv = None

        def do():
            for device in discover(ip_address, log_level):
                self.upnp_tv = device
                if self._remote is None:

                    year = self.upnp_tv.year

                    if year is not None and year <= 2014:
                        self._remote = RemoteLegacy(
                            self.upnp_tv.ip_address,
                            self.upnp_tv.device_id
                        )
                    else:
                        self._remote = RemoteWebsocket(
                            self.upnp_tv.ip_address,
                            self.upnp_tv.device_id
                        )
                break
            else:
                logger.warning('Unable to locate TV')

            self._discovering.set()

        if isinstance(config, dict):
            if config['method'] == 'legacy':
                self._remote = RemoteLegacy(config)
            else:
                self._remote = RemoteWebsocket(config)

            t = threading.Thread(target=do)
            t.daemon = True
            t.start()

        else:
            do()

    @property
    def is_discovering(self):
        return not self._discovering.isSet()

    def __enter__(self):
        return self._remote.__enter__()

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._remote.__exit__(exc_type, exc_val, exc_tb)

    def close(self):
        return self._remote.close()

    def control(self, key):
        return self._remote.control(key)

    def __getattr__(self, item):
        if item in self.__dict__:
            return self.__dict__[item]

        if self.upnp_tv is not None:
            return getattr(self.upnp_tv, item)

    def __setattr__(self, key, value):
        if key in ('_remote', 'upnp_tv'):
            object.__setattr__(self, key, value)
        else:
            if self.upnp_tv is not None:
                setattr(self.upnp_tv, key, value)


