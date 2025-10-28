# This repository automates the building and release of CPython tarballs for the `ppc64le` and `s390x` architectures, specifically for use on GitHub Actions runners and similar CI environments.

## Background

The upstream repository [`actions/python-versions`](https://github.com/actions/python-versions) is maintained by Microsoft and provides official Python binaries for GitHub Actions runners. However, as of now, Microsoft does not release pre-built Python binaries for the `ppc64le` and `s390x` architectures.

This repository fills that gap by building and publishing CPython tarballs for these architectures, following the same tags as the upstream project.

## Features

- Automated Docker-based builds for CPython targeting `ppc64le` and `s390x` architectures.
- Makefile-driven workflow for flexible version and architecture selection.
- GitHub Actions workflow to fetch tags from the upstream `actions/python-versions` repository, build Python tarballs for each tag, and upload them as release assets.
- Support for both Podman and Docker as container engines.

## Repository Structure

- `python-versions/` — Dockerfile and build scripts for Python version tarballs.
- `PowerShell/` — Multi-stage Dockerfile and patches for building custom PowerShell binaries (future extensibility).
- `Makefile` — Main entry point for building Python and PowerShell artifacts with configurable variables.
- `.github/workflows/` — GitHub Actions workflows for automation.

## Usage

### Prerequisites

- Podman or Docker
- GNU Make

### Build Python Tarball

```sh
make PYTHON_VERSION=<version> ARCH=<arch>
```

- Example: `make PYTHON_VERSION=3.13.3 ARCH=s390x`
- Example: `make PYTHON_VERSION=3.13.3 ARCH=ppc64le`

### Run All Builds

```sh
make
```

### GitHub Actions Automation

The included workflow (`.github/workflows/build-and-release-python-versions.yml`) will:

- Fetch all tags from the upstream `actions/python-versions` repository
- Build a Python tarball for each tag (for supported architectures)
- Upload the tarball as a release asset if it does not already exist

## License

Licensed under the Apache License, Version 2.0. See the `LICENSE` file or:

http://www.apache.org/licenses/LICENSE-2.0
