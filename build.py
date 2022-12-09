#!/usr/bin/env python3
#
# wireguard4netns
#
# Copyright (c) 2022 Carnegie Mellon University
# SPDX-License-Identifier: MIT
#

import os
import shutil
import subprocess
import tarfile
import urllib.request
from pathlib import Path
from tempfile import TemporaryDirectory

GOLANG = "https://storage.googleapis.com/golang/go{}.linux-amd64.tar.gz"
GOLANG_VERSION = "1.19.4"


def build(*_setup_kwargs):
    """Build wireguard-go"""
    dest = Path("src") / "wireguard4netns" / "wireguard-go"

    if dest.exists():
        print(f"{dest} already exists, skipping build")
        return

    go = shutil.which("go")
    patch = shutil.which("patch")

    # copy wireguard-go source into a temporary directory, patch and compile
    with TemporaryDirectory() as tmp:
        if go is None:
            # fetch + extract go compiler
            print(f"Downloading golang-v{GOLANG_VERSION}")
            stream = urllib.request.urlopen(GOLANG.format(GOLANG_VERSION))
            golang = tarfile.open(fileobj=stream, mode="r|gz")
            golang.extractall(path=tmp)
            go = str(Path(tmp, "go", "bin", "go").resolve())

        print("Copying wireguard-go source")
        tmp_root = Path(tmp, "wireguard-go")
        shutil.copytree("wireguard-go", tmp_root)

        # when building from a git checkout this ends up pointing at a
        # non-existent path and we don't need it, so just clean it up.
        gitlink = tmp_root.joinpath(".git")
        if gitlink.exists():
            gitlink.unlink()

        # apply patch to disable SetMTU()/MTU() because wireguard-go won't be
        # able to see the tuntap interface in the unprivileged network namespace
        print("Patching wireguard-go source")
        patchfile = Path("wireguard-go.patch")
        subprocess.run([patch, "-p1"], stdin=patchfile.open(), cwd=tmp_root, check=True)

        # to avoid downloading already cached modules
        GOMODCACHE = subprocess.run(
            [go, "env", "GOMODCACHE"], stdout=subprocess.PIPE, check=True
        ).stdout
        env = dict(os.environ, GOPATH=str(Path(tmp).resolve()), GOMODCACHE=GOMODCACHE)

        print("Building custom wireguard-go binary")
        subprocess.run([go, "get", "-d"], cwd=tmp_root, env=env, check=True)
        subprocess.run(
            [
                go,
                "build",
                "-o",
                str(dest.resolve()),
                "-ldflags=-s -w -X golang.zx2c4.com/wireguard/ipc.socketDirectory=.",
            ],
            cwd=tmp_root,
            env=env,
            check=True,
        )


if __name__ == "__main__":
    build()
