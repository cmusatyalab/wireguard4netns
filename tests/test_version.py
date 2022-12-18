# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT

from wireguard4netns import __version__


def test_version_exists() -> None:
    assert __version__
