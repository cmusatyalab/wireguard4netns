#
# wireguard4netns
#
# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT
#
__version__ = "0.1.1"

from .wireguard_daemon import create_wireguard_tunnel

__all__ = [
    "create_wireguard_tunnel",
]
