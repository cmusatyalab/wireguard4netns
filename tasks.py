# SPDX-FileCopyrightText: 2022 Carnegie Mellon University
# SPDX-License-Identifier: 0BSD

# pyinvoke file for maintenance tasks

import os
import re
from pathlib import Path

from invoke import task


@task
def update_dependencies(c):
    """Update python package dependencies"""
    # update project + pre-commit check dependencies
    c.run("poetry update")
    c.run("poetry run pre-commit autoupdate")
    # make sure project still passes pre-commit and unittests
    c.run("poetry run pre-commit run -a")
    c.run("poetry run pytest")
    # commit updates
    c.run("git commit -m 'Update dependencies' poetry.lock .pre-commit-config.yaml")


def get_current_version(c):
    """Get the current application version.
    Helm chart version should always be >= application version.
    """
    r = c.run("poetry run tbump current-version", hide="out")
    return r.stdout.strip()


def bump_current_version(c, part):
    """Simplistic version bumping."""
    current_version = get_current_version(c)
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", current_version)
    assert match is not None

    major, minor, patch = match.groups()
    if part == "major":
        return f"{int(major)+1}.0.0"
    if part == "minor":
        return f"{major}.{int(minor)+1}.0"
    return f"{major}.{minor}.{int(patch)+1}"


@task
def bump_version(c, part="patch"):
    """Bump application version"""
    # bump source version for next release
    release = bump_current_version(c, part)
    c.run(f"poetry run tbump --no-tag --no-push {release}")


@task
def build_sdist(c):
    """Build src tarball"""
    # make sure wireguard-go submodule is initialized
    assert Path("wireguard-go", "LICENSE").exists()

    # clean up old builds
    dist = Path("dist")
    for sdist in dist.glob("*.tar.gz"):
        sdist.unlink()
    for wheel in dist.glob("*.whl"):
        wheel.unlink()

    c.run("poetry build --format=sdist")


GOLANG_VERSION = "1.19.4"
SCRIPT = """\
cd /tmp
curl {golang} --silent --location | tar -xz
export PATH="/tmp/go/bin:$PATH" HOME=/tmp
for py in {pythons}; do
    "/opt/python/$py/bin/pip" wheel --no-deps --wheel-dir /tmp /dist/*.tar.gz
done
ls *.whl | xargs -n1 --verbose auditwheel repair --wheel-dir /dist
ls -al /dist
"""


@task(build_sdist)
def build_wheels(c):
    """Build wheels from the pypa/manylinux1_x86_64 Docker container

    Based on how setuptools-golang builds, but using a newer manylinux
    container and some hardcoded golang/python versions.
    """
    golang = (
        f"https://storage.googleapis.com/golang/go{GOLANG_VERSION}.linux-amd64.tar.gz"
    )
    pythons = " ".join(
        [
            "cp37-cp37m",
            "cp38-cp38",
            "cp39-cp39",
            "cp310-cp310",
            "cp311-cp311",
        ]
    )

    dist = Path("dist")
    dist.joinpath("build_wheels.sh").write_text(
        SCRIPT.format(golang=golang, pythons=pythons)
    )

    # we'd like to support Python 3.7+ and Ubuntu 18.04, but...
    # manylinux1 support ended 2022/1/1     (3.6+ / 16.04)
    # manylinux2010 support ended 2022/8/1  (3.7.3+ / 20.04)
    # manylinux2014 is still supported      (3.7.8+ / 20.04)
    c.run(
        "docker run --rm"
        f" --volume {dist.resolve()}:/dist:rw"
        f" --user {os.getuid()}:{os.getgid()}"
        " quay.io/pypa/manylinux2014_x86_64:latest"
        " bash -o pipefail -eux /dist/build_wheels.sh"
    )


@task
def tag(c):
    """Apply tag for current release and bump to dev release"""
    release = get_current_version(c)
    c.run(f"git tag -m v{release} v{release}")

    # bump version to new development tag
    new_version = f"{release}.post.dev0"
    c.run(f"poetry run tbump --non-interactive --only-patch {new_version}")
    c.run("git add --update")
    c.run(f'git commit --no-verify --message "Bumping to {new_version}"')


@task(bump_version, build_sdist, build_wheels, tag)
def publish(c, part="patch"):
    """Bump application version, build, tag and publish"""
    # publish to pypi
    c.run("poetry publish")

    # update source and tags in github
    c.run("git push")
    c.run("git push --tags")
