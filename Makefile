# ==============================================================================
# Project: Python Build System (Containerized & Secured)
# Description: Builds Python artifacts via a multi-stage container process.
#              Includes Trivy security scanning and automated artifact recovery.
# ==============================================================================

# --- Configuration & Defaults -------------------------------------------------

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c

ifeq ($(origin V), undefined)
  Q := @
else
  Q :=
endif

# Versioning
PYTHON_VERSION          ?= 3.13.3
ACTIONS_PYTHON_VERSIONS ?= 3.15.0-alpha.5-21016111327
POWERSHELL_VERSION      ?= v7.5.2
POWERSHELL_NATIVE_VERSION ?= v7.4.0
UBUNTU_VERSION          ?= 24.04
TRIVY_VERSION           ?= v0.68.2

# Security Gates (0 = Log Only, 1 = Fail Build)
FAIL_ON_CRITICAL        ?= 1
FAIL_ON_HIGH            ?= 1
FAIL_ON_MEDIUM          ?= 0
FAIL_ON_SECRET          ?= 0

# System Architecture Normalization
ARCH_RAW := $(shell uname -m)
ifeq ($(ARCH_RAW),x86_64)
  ARCH := amd64
else ifeq ($(ARCH_RAW),aarch64)
  ARCH := arm64
else
  ARCH := $(ARCH_RAW)
endif

# Container Engine Detection
CONTAINER_ENGINE := $(shell command -v podman 2>/dev/null || command -v docker)

ifeq ($(strip $(CONTAINER_ENGINE)),)
  $(error No container runtime found. Please install `docker` or `podman`)
endif

# --- Internal Variables -------------------------------------------------------

BASE_IMAGE := powershell:ubuntu-$(UBUNTU_VERSION)

# Naming conventions
OUTPUT_DIR := python-versions/output
IMAGE_NAME := python:$(PYTHON_VERSION)-ubuntu-$(UBUNTU_VERSION)-$(ARCH)
TEMP_CONTAINER_NAME := python-build-$(PYTHON_VERSION)-$(ARCH)-tmp

# [CHANGED] Separate Internal vs Host filenames
# 1. The name generated INSIDE the container (must match build-python.ps1 output)
INTERNAL_ARTIFACT_NAME := python-$(PYTHON_VERSION)-linux-$(ARCH).tar.gz

# 2. The name we save ON THE HOST (includes Ubuntu version for GitHub Workflow)
HOST_ARTIFACT_NAME := python-$(PYTHON_VERSION)-linux-$(UBUNTU_VERSION)-$(ARCH).tar.gz

# Prerequisite Files
PS_DIR := PowerShell
PS_PREREQS := \
    $(PS_DIR)/Dockerfile \
    $(PS_DIR)/patch/powershell-native-$(POWERSHELL_NATIVE_VERSION).patch \
    $(PS_DIR)/patch/powershell-$(ARCH)-$(POWERSHELL_VERSION).patch \
    $(PS_DIR)/patch/powershell-gen-$(POWERSHELL_VERSION).tar.gz

# --- Targets ------------------------------------------------------------------

.PHONY: all powershell clean help verify-gate

# Updated 'all' to target the new host artifact name
all: $(OUTPUT_DIR)/$(HOST_ARTIFACT_NAME) verify-gate

# 1. Build the Python Artifact
$(OUTPUT_DIR)/$(HOST_ARTIFACT_NAME): powershell | $(OUTPUT_DIR)
	@echo "--- Building Python $(PYTHON_VERSION) Image ($(ARCH)) ---"
	@echo "    Security Gate: CRIT=$(FAIL_ON_CRITICAL) HIGH=$(FAIL_ON_HIGH)"
	$(Q)cd python-versions && $(CONTAINER_ENGINE) build \
		--network=host \
		--build-arg PYTHON_VERSION=$(PYTHON_VERSION) \
		--build-arg ACTIONS_PYTHON_VERSIONS=$(ACTIONS_PYTHON_VERSIONS) \
		--build-arg UBUNTU_VERSION=$(UBUNTU_VERSION) \
		--build-arg TARGETARCH=$(ARCH) \
		--build-arg BASE_IMAGE=$(BASE_IMAGE) \
		--build-arg TRIVY_VERSION=$(TRIVY_VERSION) \
		--build-arg FAIL_ON_CRITICAL=$(FAIL_ON_CRITICAL) \
		--build-arg FAIL_ON_HIGH=$(FAIL_ON_HIGH) \
		--build-arg FAIL_ON_MEDIUM=$(FAIL_ON_MEDIUM) \
		--build-arg FAIL_ON_SECRET=$(FAIL_ON_SECRET) \
		-t $(IMAGE_NAME) .
	
	@echo "--- Extracting Artifacts ---"
	$(Q)$(CONTAINER_ENGINE) rm -f $(TEMP_CONTAINER_NAME) 2>/dev/null || true
	$(Q)$(CONTAINER_ENGINE) create --name $(TEMP_CONTAINER_NAME) $(IMAGE_NAME) >/dev/null
	
	@# [CHANGED] Copy from INTERNAL name -> HOST name
	@echo "Copying $(INTERNAL_ARTIFACT_NAME) -> $(HOST_ARTIFACT_NAME)"
	$(Q)$(CONTAINER_ENGINE) cp $(TEMP_CONTAINER_NAME):/tmp/artifact/$(INTERNAL_ARTIFACT_NAME) \
		$(abspath $(OUTPUT_DIR))/$(HOST_ARTIFACT_NAME)
	
	@# Copy Security Reports
	$(Q)$(CONTAINER_ENGINE) cp $(TEMP_CONTAINER_NAME):/tmp/artifact/python-$(PYTHON_VERSION)-$(ARCH).sbom.json \
		$(abspath $(OUTPUT_DIR))/python-$(PYTHON_VERSION)-linux-$(UBUNTU_VERSION)-$(ARCH).sbom.json || echo "Warning: SBOM missing"
	
	$(Q)$(CONTAINER_ENGINE) cp $(TEMP_CONTAINER_NAME):/tmp/artifact/trivy-$(PYTHON_VERSION)-$(ARCH)-vuln.json \
		$(abspath $(OUTPUT_DIR))/trivy-python-$(PYTHON_VERSION)-linux-$(UBUNTU_VERSION)-$(ARCH)-vuln.json || echo "Warning: Trivy Vuln report missing"
	
	$(Q)$(CONTAINER_ENGINE) cp $(TEMP_CONTAINER_NAME):/tmp/artifact/trivy-$(PYTHON_VERSION)-$(ARCH)-secret.json \
		$(abspath $(OUTPUT_DIR))/trivy-python-$(PYTHON_VERSION)-linux-$(UBUNTU_VERSION)-$(ARCH)-secret.json || echo "Warning: Trivy Secret report missing"
	
	$(Q)$(CONTAINER_ENGINE) cp $(TEMP_CONTAINER_NAME):/tmp/artifact/trivy-gate-result.json \
		$(abspath $(OUTPUT_DIR))/trivy-gate-result.json || echo "Warning: Trivy Gate result missing"
	$(Q)$(CONTAINER_ENGINE) cp $(TEMP_CONTAINER_NAME):/tmp/artifact/trivy-gate.log \
		$(abspath $(OUTPUT_DIR))/trivy-gate.log || echo "Warning: Gate Log missing"
	
	@# Cleanup
	$(Q)$(CONTAINER_ENGINE) rm -f $(TEMP_CONTAINER_NAME) >/dev/null
	@echo "Build complete: $(OUTPUT_DIR)/$(HOST_ARTIFACT_NAME)"

# 2. Verify Gate Results
verify-gate:
	@if [ -f "$(OUTPUT_DIR)/trivy-gate-result.json" ]; then \
		echo "--- Security Gate Summary ---"; \
		cat $(OUTPUT_DIR)/trivy-gate-result.json; \
		echo ""; \
	fi
	@if [ -f "$(OUTPUT_DIR)/trivy-gate.log" ]; then \
		echo "--- Security Gate Execution Log ---"; \
		cat $(OUTPUT_DIR)/trivy-gate.log; \
		echo ""; \
	fi

# 3. Build Base PowerShell Image
powershell: $(PS_PREREQS)
	@echo "--- Building PowerShell Base Image ---"
	$(Q)cd $(PS_DIR) && $(CONTAINER_ENGINE) build \
		--network=host \
		--build-arg POWERSHELL_VERSION=$(POWERSHELL_VERSION) \
		--build-arg POWERSHELL_NATIVE_VERSION=$(POWERSHELL_NATIVE_VERSION) \
		--build-arg UBUNTU_VERSION=$(UBUNTU_VERSION) \
		--build-arg TARGETARCH=$(ARCH) \
		--tag powershell:ubuntu-$(UBUNTU_VERSION) .

$(OUTPUT_DIR):
	$(Q)mkdir -p $@

$(PS_DIR)/patch/%.tar.gz:
	$(error Required patch file $@ is missing. Check submodule or download scripts.)

clean:
	@echo "Cleaning up artifacts and temporary containers..."
	$(Q)rm -rf $(OUTPUT_DIR)
	$(Q)$(CONTAINER_ENGINE) rm -f $(TEMP_CONTAINER_NAME) 2>/dev/null || true
	@echo "Clean complete."

help:
	@echo "Usage: make [target] [VARIABLES]"
	@echo "Targets: all, powershell, clean, help"
	@echo "Output: $(HOST_ARTIFACT_NAME)"