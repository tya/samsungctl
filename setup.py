#!/usr/bin/env python

import setuptools

__doc__ = """Remote control Samsung televisions via TCP/IP connection"""

__title__ = "samsungctl"
__version__ = "0.7.1+1"
__url__ = "https://github.com/kdschlosser/samsungctl"
__author__ = "Lauri Niskanen, Kevin Schlosser"
__author_email__ = "kevin.g.schlosser@gmail.com"
__license__ = "MIT, GNUv2"


setuptools.setup(
    name=__title__,
    version=__version__,
    description=__doc__,
    url=__url__,
    author=__author__,
    author_email=__author_email__,
    license=__license__,
    long_description=open("README.rst").read(),
    zip_safe=False,
    entry_points={
        "console_scripts": ["samsungctl=samsungctl.__main__:main"]
    },
    packages=["samsungctl", "samsungctl.upnp", "samsungctl.upnp.UPNP_Device"],
    install_requires=['requests', 'websocket-client', 'ifaddr', 'six', 'lxml'],
    extras_require={
        "interactive_ui": ["curses"],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Topic :: Home Automation",
    ],
)
