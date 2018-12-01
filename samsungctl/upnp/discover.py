# -*- coding: utf-8 -*-

from __future__ import print_function
import socket
import threading
import time
import logging
import sys
import ctypes


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

if sys.platform.startswith('win'):
    def get_local_addresses():
        from ctypes.wintypes import DWORD, BYTE, BOOL, UINT, ULONG

        CHAR = ctypes.c_char
        time_t = ctypes.c_ulong
        POINTER = ctypes.POINTER
        PULONG = POINTER(ULONG)

        MAX_ADAPTER_DESCRIPTION_LENGTH = 128
        MAX_ADAPTER_NAME_LENGTH = 256
        MAX_ADAPTER_ADDRESS_LENGTH = 8

        ERROR_SUCCESS = 0x00000000
        ERROR_BUFFER_OVERFLOW = 0x0000006F


        class _IP_ADDR_STRING(ctypes.Structure):
            pass


        IP_ADDR_STRING = _IP_ADDR_STRING
        PIP_ADDR_STRING = POINTER(_IP_ADDR_STRING)


        class IP_ADDRESS_STRING(ctypes.Structure):
            _fields_ = [
                ('String', CHAR * (4 * 4))
            ]


        PIP_ADDRESS_STRING = POINTER(IP_ADDRESS_STRING)
        IP_MASK_STRING = IP_ADDRESS_STRING
        PIP_MASK_STRING = POINTER(IP_ADDRESS_STRING)

        IP_ADDR_STRING._fields_ = [
            ("Next", POINTER(_IP_ADDR_STRING)),
            ("IpAddress", IP_ADDRESS_STRING),
            ("IpMask", IP_MASK_STRING),
            ("Context", DWORD)
        ]


        class _IP_ADAPTER_INFO(ctypes.Structure):
            pass


        IP_ADAPTER_INFO = _IP_ADAPTER_INFO
        PIP_ADAPTER_INFO = POINTER(_IP_ADAPTER_INFO)

        IP_ADAPTER_INFO._fields_ = [
            ("Next", POINTER(_IP_ADAPTER_INFO)),
            ("ComboIndex", DWORD),
            ("AdapterName", CHAR * (MAX_ADAPTER_NAME_LENGTH + 4)),
            ("Description", CHAR * (MAX_ADAPTER_DESCRIPTION_LENGTH + 4)),
            ("AddressLength", UINT),
            ("Address", BYTE * MAX_ADAPTER_ADDRESS_LENGTH),
            ("Index", DWORD),
            ("Type", UINT),
            ("DhcpEnabled", UINT),
            ("CurrentIpAddress", PIP_ADDR_STRING),
            ("IpAddressList", IP_ADDR_STRING),
            ("GatewayList", IP_ADDR_STRING),
            ("DhcpServer", IP_ADDR_STRING),
            ("HaveWins", BOOL),
            ("PrimaryWinsServer", IP_ADDR_STRING),
            ("SecondaryWinsServer", IP_ADDR_STRING),
            ("LeaseObtained", time_t),
            ("LeaseExpires", time_t)
        ]

        iphlpapi = ctypes.windll.iphlpapi

        GetAdaptersInfo = iphlpapi.GetAdaptersInfo
        GetAdaptersInfo.restype = ULONG
        GetAdaptersInfo.argtypes = [PIP_ADAPTER_INFO, PULONG]

        adapter_list = (IP_ADAPTER_INFO * 1)()
        buf_len = ULONG(ctypes.sizeof(adapter_list))
        rc = GetAdaptersInfo(ctypes.byref(adapter_list[0]),
            ctypes.byref(buf_len))

        if rc == ERROR_BUFFER_OVERFLOW:
            adapter_list = (
                IP_ADAPTER_INFO * (
                buf_len.value / ctypes.sizeof(IP_ADAPTER_INFO))
            )()

            buf_len = ULONG(ctypes.sizeof(adapter_list))
            rc = GetAdaptersInfo(
                ctypes.byref(adapter_list[0]),
                ctypes.byref(buf_len)
            )

        if rc == ERROR_SUCCESS:
            for a in adapter_list:
                address_list = a.IpAddressList
                while True:
                    ip_address = address_list.IpAddress.String
                    if ip_address:
                        yield ip_address
                    address_list = address_list.Next
                    if not address_list:
                        break

        else:
            raise ctypes.WinError()

else:
    import ctypes.util

    USHORT = ctypes.c_ushort
    BYTE = ctypes.c_byte
    PVOID = ctypes.c_void_p
    PCHAR = ctypes.c_char_p
    UINT = ctypes.c_uint
    UINT8 = ctypes.c_uint8
    UINT16 = ctypes.c_uint16
    UINT32 = ctypes.c_uint32

    POINTER = ctypes.POINTER


    class struct_sockaddr(ctypes.Structure):
        if sys.platform == 'darwin':
            _fields_ = [
                ('sa_len', UINT8),
                ('sa_family', UINT8),
                ('sa_data', BYTE * 14)
            ]

        else:
            _fields_ = [
                ('sa_family', USHORT),
                ('sa_data', BYTE * 14)
            ]


    class struct_sockaddr_in(ctypes.Structure):
        if sys.platform == 'darwin':
            _fields_ = [
                ('sin_len', UINT8),
                ('sin_family', UINT8),
                ('sin_port', UINT16),
                ('sin_addr', BYTE * 4),
                ('sin_zero', BYTE * 8)
            ]
        else:
            _fields_ = [
                ('sin_family', USHORT),
                ('sin_port', UINT16),
                ('sin_addr', BYTE * 4)
            ]


    class struct_sockaddr_in6(ctypes.Structure):
        if sys.platform == 'darwin':
            _fields_ = [
                ('sin6_len', UINT8),
                ('sin6_family', UINT8),
                ('sin6_port', UINT16),
                ('sin6_flowinfo', UINT32),
                ('sin6_addr', BYTE * 16),
                ('sin6_scope_id', UINT32)
            ]

        else:
            _fields_ = [
                ('sin6_family', USHORT),
                ('sin6_port', UINT16),
                ('sin6_flowinfo', UINT32),
                ('sin6_addr', BYTE * 16),
                ('sin6_scope_id', UINT32)
            ]


    class struct_ifaddrs(ctypes.Structure):
        pass


    if sys.platform == 'darwin':
        struct_ifaddrs._fields_ = [
            ('ifa_next', POINTER(struct_ifaddrs)),
            ('ifa_name', PCHAR),
            ('ifa_flags', UINT),
            ('ifa_addr', POINTER(struct_sockaddr)),
            ('ifa_netmask', POINTER(struct_sockaddr)),
            ('ifa_dstaddr', POINTER(struct_sockaddr)),
            ('ifa_data', PVOID)
        ]

    else:
        class union_ifa_ifu(ctypes.Union):
            _fields_ = [
                ('ifu_broadaddr', POINTER(struct_sockaddr)),
                ('ifu_dstaddr', POINTER(struct_sockaddr))
            ]


        struct_ifaddrs._fields_ = [
            ('ifa_next', POINTER(struct_ifaddrs)),
            ('ifa_name', PCHAR),
            ('ifa_flags', UINT),
            ('ifa_addr', POINTER(struct_sockaddr)),
            ('ifa_netmask', POINTER(struct_sockaddr)),
            ('ifa_ifu', union_ifa_ifu),
            ('ifa_data', PVOID)
        ]

    libc = ctypes.CDLL(ctypes.util.find_library('c'))


    def get_local_addresses():
        ifap = POINTER(struct_ifaddrs)()
        result = libc.getifaddrs(ctypes.pointer(ifap))

        if result != 0:
            raise OSError(ctypes.get_errno())
        del result

        try:
            ifa = ifap.contents
            while True:
                sa = ifa.ifa_addr.contents
                family = sa.sa_family
                if family == socket.AF_INET:
                    sa = ctypes.cast(
                        ctypes.pointer(sa),
                        POINTER(struct_sockaddr_in)
                    ).contents

                    addr = socket.inet_ntop(family, sa.sin_addr)
                    if addr != '127.0.0.1':
                        yield addr

                if not ifa.ifa_next:
                    break

                ifa = ifa.ifa_next.contents

        finally:
            libc.freeifaddrs(ifap)


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

    from . import UPNPTV

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

    for sock_addr in get_local_addresses():
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

