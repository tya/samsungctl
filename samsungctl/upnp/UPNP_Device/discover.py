# -*- coding: utf-8 -*-

from __future__ import print_function
import socket
import threading
import ifaddr
import ipaddress
import sys

import logging
logger = logging.getLogger('UPNP_Devices')
logger.setLevel(logging.NOTSET)


if sys.platform.startswith('win'):
    IPPROTO_IPV6 = 41
else:
    IPPROTO_IPV6 = getattr(socket, 'IPPROTO_IPV6')


IPV4_MCAST_GRP = "239.255.255.250"
IPV6_MCAST_GRP = "[ff02::c]"


IPV4_SSDP = '''M-SEARCH * HTTP/1.1\r
ST: upnp:rootdevice\r
MAN: "ssdp:discover"\r
HOST: 239.255.255.250:1900\r
MX: 1\r
Content-Length: 0\r
\r
'''


IPV6_SSDP = '''M-SEARCH * HTTP/1.1\r
ST: upnp:rootdevice\r
MAN: "ssdp:discover"\r
HOST: [ff02::c]:1900\r
MX: 1\r
Content-Length: 0\r
\r
'''

adapter_ips = []

for adapter in ifaddr.get_adapters():
    for adapter_ip in adapter.ips:
        if isinstance(adapter_ip.ip, tuple):
            continue
        else:
            adapter_ips += [adapter_ip.ip]


def _send_to(destination, t_out=5):
    try:
        network = ipaddress.ip_network(destination.decode('utf-8'))
    except:
        network = ipaddress.ip_network(destination)

    if isinstance(network, ipaddress.IPv6Network):
        mcast = IPV6_MCAST_GRP
        ssdp_packet = IPV6_SSDP
        sock = socket.socket(
            family=socket.AF_INET6,
            type=socket.SOCK_DGRAM,
            proto=socket.IPPROTO_IP
        )
        sock.setsockopt(IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, 1)

    else:
        mcast = IPV4_MCAST_GRP
        ssdp_packet = IPV4_SSDP
        sock = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_DGRAM,
            proto=socket.IPPROTO_UDP
        )
        sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)

    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    if destination in adapter_ips:
        sock.bind((destination, 0))
        destination = mcast

    sock.settimeout(t_out)

    logger.debug('SSDP: %s\n%s', destination, ssdp_packet)
    for _ in range(5):
        sock.sendto(ssdp_packet.encode('utf-8'), (destination, 1900))
    return sock


def get_upnp_classes(ip, timeout=8, log_level=logging.NOTSET):
    logger.setLevel(log_level)
    sock = _send_to(ip, timeout)
    locations = []

    while True:
        try:
            data, addr = sock.recvfrom(1024)
        except socket.timeout:
            break

        addr = addr[0]
        logger.debug('SSDP: %s - > %s', addr, data)
        data = data.decode('utf-8').split('\n', 1)[1]

        packet = dict(
            (
                line.split(':', 1)[0].strip().upper(),
                line.split(':', 1)[1].strip()
            ) for line in data.split('\n')
            if line.strip()
        )

        if 'LOCATION' not in packet or packet['LOCATION'] in locations:
            continue

        locations += [packet['LOCATION']]
        logger.debug(
            'SSDP: %s found LOCATION: %s',
            addr,
            packet['LOCATION']
        )

        if 'NT' in packet:
            logger.debug(
                'SSDP: %s found NT: %s',
                addr,
                packet['NT']
            )
        if 'ST' in packet:
            logger.debug(
                'SSDP: %s found ST: %s',
                addr,
                packet['ST']
            )

    return locations


def discover(timeout=5, log_level=logging.NOTSET):
    logger.setLevel(log_level)

    ips = []
    found = []
    found_event = threading.Event()
    threads = []

    def do(local_address):
        sock = _send_to(local_address, timeout)

        while True:
            try:
                _, addr = sock.recvfrom(1024)
            except socket.timeout:
                break

            addr = addr[0]
            if addr in ips:
                continue

            logger.debug('SSDP: connected ip ' + addr)

            ips.append(addr)
            found.append(addr)
            found_event.set()

        try:
            sock.close()
        except socket.error:
            pass

        if len(threads) == 1:
            found_event.set()

        threads.remove(threading.current_thread())

    for ip in adapter_ips:
        t = threading.Thread(
            target=do,
            args=(ip,)
        )
        t.daemon = True
        threads += [t]
        t.start()

    while threads:
        found_event.wait()
        found_event.clear()
        while found:
            yield found.pop(0)


if __name__ == '__main__':
    from logging import NullHandler

    logger.addHandler(NullHandler())
    for device in discover(5, logging.DEBUG):
        print(device)
