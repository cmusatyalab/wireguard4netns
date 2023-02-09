# WireGuard VPN networking for unprivileged network namespaces

wireguard4netns is directly inspired by the awesome work of the authors of
[slirp4netns](https://github.com/rootless-containers/slirp4netns). Instead of
providing generic user-mode networking for unprivileged network namespaces
through libslirp, wireguard4netns brings network access to the containers
through [wireguard-go](https://git.zx2c4.com/wireguard-go/about/), a userspace
WireGuard VPN tunnel implementation.


## Motivation

We were building a framework for developing Edge-Native applications (the
[Sinfonia](https://github.com/cmusatyalab/sinfonia/) project) and for this we
split applications into two primary components, a frontend that runs on the
user's device and a backend consisting of one or more services are deployed on
a nearby Kubernetes cluster (`cloudlet`).  We leverage WireGuard tunnels
between the two to avoid having to expose deployed services to the world, the
frontend's network environment is as if it was part of the same deployment
inside the same Kubernetes cluster and namespace as the backend.  This hides
most of the unnecessary network details from the application's frontend and
provides other advantages such as privacy and network mobility.

The main disadvantage was that root privileges are needed to create, configure
and attach the in-kernel WireGuard interface to a network namespace. This
required either sudo access by the user, or an administrator installed setuid
root binary helper. However slirp4netns showed the path to an alternative
approach, create a tuntap interface inside the unprivileged network namespace
and pass the control socket back to the default namespace where (in our case) a
userspace WireGuard implementation is started. All frontend traffic is then
sent through the tunnel to a VPN endpoint on the nearby cloudlet which passes
it along to the deployed namespace of the application's backend.

## Building from source

Make sure you initialize and update the wireguard-go git-submodule.

```sh
    git clone ... wireguard4netns
    cd wireguard4netns/
    git submodule update --init
    poetry build
```

This will download a copy of golang and build a custom `wireguard-go` binary
which will be placed at `src/wireguard4netns/wireguard-go`. As long as that
binary is present it will not try to rebuild the wireguard-go code again.

We use a custom built version of wireguard-go because starting with an existing
tunnel socket fd is really just an artifact of how the unmodified wireguard-go
process sets up the tuntap device and uapi socket in the foreground and then
daemonizes itself, passing along the already open file descriptors. With our
approach the tuntap device ends up being created in a different network
namespace and wireguard-go was unable to query or set the MTU. Our modification
simply changes the code to not failing when MTU operations are not working and
is in `wireguard-go.patch`.

We also needed to make sure the UAPI socket is placed in a user-writable
location instead of `/var/run/wireguard`, this `socketDirectory` path is
customized through a custom linker flag that is set in `build.py` when we
build the binary.


## Licenses

wireguard4netns is MIT licensed

    Copyright (c) 2022-2023 Carnegie Mellon University
    SPDX-License-Identifier: MIT

    Permission is hereby granted, free of charge, to any person obtaining a copy of
    this software and associated documentation files (the "Software"), to deal in
    the Software without restriction, including without limitation the rights to
    use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
    of the Software, and to permit persons to whom the Software is furnished to do
    so, subject to the following conditions:

    The above copyright notice and this permission notice shall be included in all
    copies or substantial portions of the Software.

    THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
    IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
    FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
    AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
    LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
    OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
    SOFTWARE.

wireguard-go is MIT licensed

    Copyright (C) 2017-2022 WireGuard LLC. All Rights Reserved.
    License: MIT

    see wireguard-go/LICENSE and wireguard-go/README.md

"WireGuard" is a registered trademark of Jason A. Donenfeld.
