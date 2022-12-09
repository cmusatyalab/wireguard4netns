#
# wireguard4netns
#
# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT
#

from __future__ import annotations

import argparse
from pathlib import Path

from wireguard_tools import WireguardConfig

from . import __version__
from .wireguard_daemon import create_wireguard_tunnel


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument("--tmpdir", type=Path, default=".")
    parser.add_argument("ns_pid", type=int)
    parser.add_argument("interface")
    parser.add_argument("config", metavar="wireguard.conf", type=argparse.FileType("r"))
    args = parser.parse_args()

    wg_config = WireguardConfig.from_wgconfig(args.config)
    create_wireguard_tunnel(args.ns_pid, args.interface, wg_config, args.tmpdir)
    return 0
