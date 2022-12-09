#
# wireguard4netns
#
# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT
#
"""Create a TUN device in an unprivileged network namespace"""

from __future__ import annotations

import ctypes
import ctypes.util
import errno
import fcntl
import os
import struct
from multiprocessing import Pipe, Process
from multiprocessing.connection import Connection
from multiprocessing.reduction import recv_handle, send_handle
from pathlib import Path

from pyroute2 import NDB
from typing_extensions import Literal

_libc = ctypes.CDLL(ctypes.util.find_library("c"), use_errno=True)


def setns(target_ns_pid: int, ns_type: Literal["user", "net"]) -> None:
    ns_path = Path("/proc", str(target_ns_pid), "ns", ns_type)
    with ns_path.open() as nsfd:
        if _libc.setns(nsfd.fileno(), 0) == -1:
            e = ctypes.get_errno()
            raise OSError(e, errno.errorcode[e])


def _create_tun_child(target_ns_pid: int, tundev_name: str, writer: Connection) -> None:
    # join target user and network namespaces
    setns(target_ns_pid, "user")
    setns(target_ns_pid, "net")

    tundev = os.open("/dev/net/tun", os.O_RDWR)
    assert tundev != -1

    TUNSETIFF = 0x400454CA
    IFF_TUN = 0x0001

    # create tuntap device
    ifreq = struct.pack("16sH22x", tundev_name.encode(), IFF_TUN)
    fcntl.ioctl(tundev, TUNSETIFF, ifreq)

    # pass tunnel device handle back to parent
    send_handle(writer, tundev, None)

    # set interface mtu
    with NDB() as ndb:
        ndb.interfaces[tundev_name].set("mtu", 1420).commit()


def create_tun_in_netns(target_ns_pid: int, tundev_name: str) -> int:
    reader, writer = Pipe()
    p = Process(target=_create_tun_child, args=(target_ns_pid, tundev_name, writer))
    p.start()
    tundev = recv_handle(reader)
    p.join()
    return tundev
