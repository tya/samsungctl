# -*- coding: utf-8 -*-

from __future__ import print_function
import socket
import threading
import time
import logging

logger = logging.getLogger('samsungctl')


MCAST_GRP = "239.255.255.250"

REQUEST = [
    b'M-SEARCH * HTTP/1.1\r\n',
    b'HOST: 239.255.255.250:1900\r\n',
    b'MAN: "ssdp:discover"\r\n',
    b'MX: 1\r\n',
    None,
    b'CONTENT-LENGTH: 0\r\n\r\n'
]


def discover(timeout=5):
    # Received 6/11/2018 at 9:38:51 AM (828)
    #
    # HTTP/1.1 200 OK
    # CACHE-CONTROL: max-age = 1800
    # EXT:
    # LOCATION: http://192.168.1.63:52235/rcr/RemoteControlReceiver.xml
    # SERVER: Linux/9.0 UPnP/1.0 PROTOTYPE/1.0
    # ST: urn:samsung.com:device:RemoteControlReceiver:1
    # USN: uuid:2007e9e6-2ec1-f097-f2df-944770ea00a3::urn:samsung.com:device:
    #           RemoteControlReceiver:1
    # CONTENT-LENGTH: 0

    from samsungctl.upnp import UPNPTV

    ips = []
    found = {}
    found_lock = threading.Lock()
    found_event = threading.Event()

    threads = []

    def do(local_address):
        start = time.time()
        sock = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_DGRAM,
            proto=socket.IPPROTO_UDP
        )
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 3)
        sock.bind(local_address)
        sock.settimeout(3.0)

        def send_discover(found_st=b''):
            sts = [
                b'urn:samsung.com:device:RemoteControlReceiver:1',
                b'urn:schemas-upnp-org:device:MediaRenderer:1',
                b'urn:samsung.com:device:MainTVServer2:1'
            ]
            if found_st in sts:
                sts.remove(found_st)

            for send_st in sts:
                request = REQUEST[:]
                request[4] = b'ST: ' + send_st + b'\r\n'
                req = b''

                for itm in request:
                    req += itm

                logger.debug('SSDP: %s\n%s', local_address, req)

                for _ in range(5):
                    sock.sendto(req, ("239.255.255.250", 1900))

        send_discover()
        while True:
            try:
                data, addr = sock.recvfrom(1024)
            except socket.timeout:
                stop = time.time()
                stop = stop - start
                if stop >= timeout:
                    break

                sock_timeout = timeout - stop
                if sock_timeout > 3:
                    sock_timeout = 3

                sock.settimeout(sock_timeout)
                send_discover()
                continue

            addr = addr[0]

            if addr in ips:
                continue

            logger.debug('SSDP: %s - > %s', addr, data)

            start = data.lower().find(b'st:')

            if start > -1:
                start += 3
                st = data[start:]
                st = st[:st.find(b'\n')].strip()
            else:
                continue

            start = data.lower().find(b'location:')

            if start > -1:
                start += 9
                location = data[start:]
                location = location[:location.find(b'\n')].strip()
            else:
                continue

            with found_lock:
                if addr not in found:
                    found[addr] = {}

                if st in found[addr]:
                    continue

                found[addr][st] = location

                if len(list(found[addr].keys())) == 3:
                    ips.append(addr)
                    found_event.set()
                else:
                    send_discover(st)

        try:
            sock.close()
        except socket.error:
            pass

        threads.remove(threading.current_thread())
        found_event.set()

    for item in socket.getaddrinfo('', None, socket.AF_INET):
        fam, sock_addr = item[0], item[-1]
        t = threading.Thread(
            target=do,
            args=(sock_addr,)
        )
        t.daemon = True
        threads += [t]
        t.start()

    def get_device():
        found_lock.acquire()
        for key, value in list(found.items())[:]:
            if len(list(value.keys())) == 3:
                del found[key]

                yield UPNPTV(
                    key,
                    value[b'urn:samsung.com:device:MainTVServer2:1'],
                    value[b'urn:schemas-upnp-org:device:MediaRenderer:1'],
                    value[b'urn:samsung.com:device:RemoteControlReceiver:1']
                )

        found_event.clear()
        found_lock.release()

    while threads:
        found_event.wait()
        for dev in get_device():
            yield dev

    for dev in get_device():
        yield dev


if __name__ == '__main__':
    import sys
    import os

    sys.path.insert(
        0,
        os.path.abspath(os.path.join(os.getcwd(), '..', '..'))
    )

    if '--debug' in sys.argv:
        logger.setLevel(logging.DEBUG)
    else:
        logging.disable(logging.DEBUG)
    # logging.disable(logging.WARNING)
    # logging.disable(logging.INFO)
    for f_device in discover(10):
        print(f_device)
        print(f_device.device_id)

