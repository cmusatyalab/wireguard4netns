#
# wireguard4netns
#
# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT
#
"""Fork wireguard-go process and configure the tunnel"""

from __future__ import annotations

import os
import subprocess
import time
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator

import importlib_resources
from wireguard_tools import WireguardConfig
from wireguard_tools.wireguard_uapi import WireguardUAPIDevice

from .tundev import create_tun_in_netns


@contextmanager
def fork_wireguard_go(
    ns_pid: int, interface: str, tmpdir: Path
) -> Iterator[WireguardUAPIDevice]:

    # locate wireguard-go binary
    wireguard_go = importlib_resources.files("wireguard4netns").joinpath("wireguard-go")

    tundev = create_tun_in_netns(ns_pid, interface)
    try:
        subprocess.Popen(
            [wireguard_go, interface],
            env=dict(
                WG_PROCESS_FOREGROUND="1",
                WG_TUN_FD=str(tundev),
                # LOG_LEVEL="debug",
            ),
            pass_fds=(tundev,),
            cwd=tmpdir,
        )
    except FileNotFoundError:
        os.close(tundev)
        raise

    # wait for uapi socket
    uapi_path = Path(tmpdir, interface).with_suffix(".sock")
    while not uapi_path.exists():
        time.sleep(0.1)

    with closing(WireguardUAPIDevice(uapi_path)) as device:
        yield device

    # do we even care to wait for the child to exit?
    # no we don't, it will terminate when the device or tmpdir are cleaned up


def create_wireguard_tunnel(
    ns_pid: int, interface: str, wg_config: WireguardConfig, tmpdir: Path | None = None
) -> None:
    if tmpdir is None:
        tmpdir = Path()

    with fork_wireguard_go(ns_pid, interface, tmpdir) as wg_device:
        wg_device.set_config(wg_config)
