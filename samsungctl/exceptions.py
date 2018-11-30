class SamsungTVError(Exception):
    """Samsung TV Exception Base Class"""

    def __str__(self):
        return self.__class__.__doc__


class AccessDenied(SamsungTVError):
    """Connection was denied."""
    pass


class ConnectionClosed(SamsungTVError):
    """Connection was closed."""
    pass


class UnhandledResponse(SamsungTVError):
    """Received unknown response."""
    pass


class UnknownMethod(SamsungTVError):
    """Unknown method."""
    pass


class NoTVFound(SamsungTVError):
    """ Unable to locate a TV"""
    pass
