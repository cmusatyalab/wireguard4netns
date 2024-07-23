#
# wireguard4netns
#
# Copyright (c) 2022-2023 Carnegie Mellon University
# SPDX-License-Identifier: MIT
#
__version__ = "0.1.6.post.dev0"

from .wireguard_daemon import create_wireguard_tunnel

__all__ = [
    "create_wireguard_tunnel",
]
