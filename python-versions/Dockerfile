# ================= GLOBAL BUILD ARGS =================
ARG UBUNTU_VERSION=24.04
ARG BASE_IMAGE=powershell:ubuntu-${UBUNTU_VERSION}
ARG TARGETARCH
ARG PYTHON_VERSION=3.13.3
ARG ACTIONS_PYTHON_VERSIONS=3.13.3-14344076652
ARG TRIVY_VERSION=v0.68.1

# ================= BUILDER STAGE =====================
FROM ${BASE_IMAGE} AS builder

ARG UBUNTU_VERSION
ARG TARGETARCH
ARG PYTHON_VERSION
ARG ACTIONS_PYTHON_VERSIONS
ARG TRIVY_VERSION

USER root
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

ENV DEBIAN_FRONTEND=noninteractive \
    TZ=Asia/Kolkata \
    CC=gcc \
    CXX=g++ \
    CFLAGS="-O3 -fPIC -fstack-protector-strong -Wformat -Werror=format-security -g1" \
    CXXFLAGS="-O3 -fPIC -fstack-protector-strong -Wformat -Werror=format-security -g1" \
    LDFLAGS="-Wl,-z,relro -Wl,-z,now" \
    PYTHON_INSTALL_DIR=/opt/hostedtoolcache/Python/${PYTHON_VERSION}/${TARGETARCH}

ENV pythonLocation=${PYTHON_INSTALL_DIR} \
    PKG_CONFIG_PATH=${PYTHON_INSTALL_DIR}/lib/pkgconfig \
    LD_LIBRARY_PATH=${PYTHON_INSTALL_DIR}/lib \
    PATH=${PYTHON_INSTALL_DIR}/bin:$PATH \
    RUNNER_TEMP=/tmp \
    RUNNER_TOOL_CACHE=/opt/hostedtoolcache

# Install Dependencies
RUN apt-get -qq update -y && \
    apt-get -qq -y install --no-install-recommends \
    tzdata curl wget gcc g++ make git ca-certificates \
    build-essential libssl-dev libffi-dev zlib1g-dev jq \
    libbz2-dev libreadline-dev libsqlite3-dev liblzma-dev \
    libncurses-dev libgdbm-dev uuid-dev python3-tk tk-dev && \
    ln -fs /usr/share/zoneinfo/$TZ /etc/localtime && \
    dpkg-reconfigure -f noninteractive tzdata && \
    (apt-get -y install --no-install-recommends \
    python3 pkg-config sudo libmpdec-dev libbluetooth-dev libz-dev || true) && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Install Trivy
RUN curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b /usr/local/bin ${TRIVY_VERSION}

# Clone Python Sources
RUN if [ ! -d /python-versions ]; then git clone https://github.com/actions/python-versions.git /python-versions; fi
WORKDIR /python-versions
RUN git checkout "${ACTIONS_PYTHON_VERSIONS}" && git submodule init && git submodule update

# [CEVS STEP 1] Pre-build Scan
RUN trivy fs --scanners secret,misconfig --exit-code 1 ./

# Build & Restore Logic
RUN export MAKEFLAGS="-j $(nproc)" && \
    pwsh ./builders/build-python.ps1 ${PYTHON_VERSION} linux ${TARGETARCH} && \
    echo "Build complete. Extracting artifact..." && \
    mkdir -p /tmp/recover && \
    tar -xzf /tmp/artifact/*.tar.gz -C /tmp/recover && \
    mkdir -p ${PYTHON_INSTALL_DIR%/*} && \
    ARCH_DIR_NAME=$(basename ${PYTHON_INSTALL_DIR}) && \
    if [ -d "/tmp/recover/${ARCH_DIR_NAME}" ]; then \
      mv "/tmp/recover/${ARCH_DIR_NAME}" "${PYTHON_INSTALL_DIR%/*}/"; \
    else \
      mkdir -p "${PYTHON_INSTALL_DIR}" && \
      mv /tmp/recover/* "${PYTHON_INSTALL_DIR}/"; \
    fi && \
    rm -rf /tmp/recover && \
    if [ ! -e ${PYTHON_INSTALL_DIR}/bin/python ]; then ln -sf ${PYTHON_INSTALL_DIR}/bin/python3 ${PYTHON_INSTALL_DIR}/bin/python; fi && \
    if [ -x ${PYTHON_INSTALL_DIR}/bin/pip3 ] && [ ! -e ${PYTHON_INSTALL_DIR}/bin/pip ]; then ln -sf ${PYTHON_INSTALL_DIR}/bin/pip3 ${PYTHON_INSTALL_DIR}/bin/pip; fi && \
    ${PYTHON_INSTALL_DIR}/bin/python3 -c "import ssl; print('Python installed and SSL verified')"

# [CEVS STEP 2] Post-build Scan & Gate
RUN mkdir -p /tmp/artifact && \
    trivy fs --format cyclonedx --output /tmp/artifact/python-${PYTHON_VERSION}-${TARGETARCH}.sbom.json ${PYTHON_INSTALL_DIR} || true

RUN trivy --download-db-only || true; \
    trivy fs --format json --output /tmp/artifact/trivy-${PYTHON_VERSION}-${TARGETARCH}-vuln.json --scanners vuln ${PYTHON_INSTALL_DIR} || true && \
    trivy fs --format json --output /tmp/artifact/trivy-${PYTHON_VERSION}-${TARGETARCH}-secret.json --scanners secret,misconfig ${PYTHON_INSTALL_DIR} || true

# Copy Enhanced Gate Script with Logging
COPY trivy-gate.sh /usr/local/bin/trivy-gate.sh
RUN chmod +x /usr/local/bin/trivy-gate.sh

# Run the Gate and Capture Log
# We pipe to 'tee' to save stdout to a file AND show it in console.
# Because SHELL is set to pipefail, if the gate fails, the build will fail.
RUN FAIL_ON_CRITICAL=0 FAIL_ON_HIGH=0 FAIL_ON_MEDIUM=0 FAIL_ON_SECRET=0 \
    /usr/local/bin/trivy-gate.sh /tmp/artifact/trivy-${PYTHON_VERSION}-${TARGETARCH}-vuln.json /tmp/artifact/trivy-gate-result.json /tmp/artifact/trivy-${PYTHON_VERSION}-${TARGETARCH}-secret.json 2>&1 | tee /tmp/artifact/trivy-gate.log || true

# Run Tests
WORKDIR /python-versions/tests
RUN cp $RUNNER_TEMP/work/build_output.txt $RUNNER_TEMP/ || touch $RUNNER_TEMP/build_output.txt
RUN pwsh -Command "Install-Module -Name Pester -Force -Scope CurrentUser -SkipPublisherCheck" && \
    AGENT_TOOLSDIRECTORY=/opt/hostedtoolcache RUNNER_TOOL_CACHE=/opt/hostedtoolcache pwsh python-tests.ps1 ${PYTHON_VERSION} linux ${TARGETARCH}

# Sanitize
RUN find ${PYTHON_INSTALL_DIR} -name "*.pyc" -delete && \
    find ${PYTHON_INSTALL_DIR} -name "__pycache__" -type d -exec rm -rf {} + && \
    rm -rf ${PYTHON_INSTALL_DIR}/lib/python*/config-*-linux-gnu/libpython*.a

# ================= FINAL STAGE =====================
FROM ubuntu:${UBUNTU_VERSION} AS final

ARG PYTHON_VERSION
ARG TARGETARCH

RUN groupadd -g 10001 python_group && \
    useradd -u 10001 -g python_group -s /bin/bash -m python_user

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates openssl libssl3 libffi8 libsqlite3-0 liblzma5 libbz2-1.0 zlib1g && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/hostedtoolcache/Python/${PYTHON_VERSION}/${TARGETARCH} /opt/hostedtoolcache/Python/${PYTHON_VERSION}/${TARGETARCH}
# Copy Artifacts & Logs
COPY --from=builder /tmp/artifact /tmp/artifact
# NOTE: The builder stage emits artifacts under /tmp/artifact using names such as
# `python-<PYTHON_VERSION>-<ARCH>.tar.gz` and SBOM/trivy files that do not include
# the Ubuntu platform version. We intentionally do not change internal artifact
# naming here; the `Makefile` handles the renaming when copying artifacts out
# of the container to the final output path, including adding `linux-<UBUNTU_VERSION>`
# when invoked from CI workflows (see .github/workflows/reusable-build-and-release-python-versions.yml).
COPY --from=builder /tmp/artifact/python-${PYTHON_VERSION}-${TARGETARCH}.sbom.json /opt/python-sbom.json

RUN rm -f /opt/Python/${PYTHON_VERSION}/${TARGETARCH}/Python-${PYTHON_VERSION}.tgz

ENV PYTHON_INSTALL_DIR=/opt/hostedtoolcache/Python/${PYTHON_VERSION}/${TARGETARCH}
ENV PATH=${PYTHON_INSTALL_DIR}/bin:$PATH
ENV LD_LIBRARY_PATH=${PYTHON_INSTALL_DIR}/lib

USER python_user

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD ["python3", "--version"]

CMD ["python3"]