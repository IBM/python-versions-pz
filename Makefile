PYTHON_VERSION ?= 3.13.3
ACTIONS_PYTHON_VERSIONS ?= 3.13.3-14344076652
POWERSHELL_VERSION ?= v7.5.2
POWERSHELL_NATIVE_VERSION ?= v7.4.0
ARCH ?= $(shell uname -m)
UBUNTU_VERSION ?= 24.04
BASE_IMAGE ?= powershell:ubuntu-$(UBUNTU_VERSION)
CONTAINER_ENGINE := $(shell command -v podman 2>/dev/null || command -v docker)

ifeq ($(findstring podman,$(CONTAINER_ENGINE)),podman)
	ifeq ($(shell uname),Linux)
		VOLUME_FLAG := -v $(abspath ./python-versions/output):/tmp/artifact:z
	else
		VOLUME_FLAG := -v ./python-versions/output:/tmp/artifact:z
	endif
else
	VOLUME_FLAG := -v ./python-versions/output:/tmp/artifact
endif

all: python-versions/output/python-$(PYTHON_VERSION)-linux-$(ARCH).tar.gz

.PHONY: powershell

python-versions/output/python-$(PYTHON_VERSION)-linux-$(ARCH).tar.gz: powershell
	cd python-versions; \
	mkdir -p output; \
	$(CONTAINER_ENGINE) build \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--build-arg ACTIONS_PYTHON_VERSIONS=$(ACTIONS_PYTHON_VERSIONS) \
		--build-arg UBUNTU_VERSION=$(UBUNTU_VERSION) \
		--build-arg TARGETARCH=$(ARCH) \
		--build-arg BASE_IMAGE=$(BASE_IMAGE) \
		-t python:$(PYTHON_VERSION)-ubuntu-$(UBUNTU_VERSION)-$(ARCH) . || exit 1; \
	container_id=`$(CONTAINER_ENGINE) create python:$(PYTHON_VERSION)-ubuntu-$(UBUNTU_VERSION)-$(ARCH)`; \
	$(CONTAINER_ENGINE) cp $$container_id:/tmp/artifact/python-$(PYTHON_VERSION)-linux-$(ARCH).tar.gz output/python-$(PYTHON_VERSION)-linux-$(UBUNTU_VERSION)-$(ARCH).tar.gz; \
	$(CONTAINER_ENGINE) rm $$container_id

powershell: PowerShell/Dockerfile \
	PowerShell/patch/powershell-native-$(POWERSHELL_NATIVE_VERSION).patch \
	PowerShell/patch/powershell-$(ARCH)-$(POWERSHELL_VERSION).patch \
	PowerShell/patch/powershell-gen-$(POWERSHELL_VERSION).tar.gz
	cd PowerShell; \
	$(CONTAINER_ENGINE) build \
		--build-arg POWERSHELL_VERSION=$(POWERSHELL_VERSION) \
		--build-arg POWERSHELL_NATIVE_VERSION=$(POWERSHELL_NATIVE_VERSION) \
		--build-arg UBUNTU_VERSION=$(UBUNTU_VERSION) \
		--build-arg TARGETARCH=$(ARCH) \
		--tag powershell:ubuntu-$(UBUNTU_VERSION) .

# Pattern rule to help diagnose missing patch files
PowerShell/patch/%.tar.gz:
	@if [ ! -f "$@" ]; then \
		echo "Error: Required patch file $@ is missing."; \
		exit 1; \
	fi
