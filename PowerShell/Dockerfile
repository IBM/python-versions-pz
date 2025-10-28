ARG UBUNTU_VERSION=24.04
ARG TARGETARCH
ARG POWERSHELL_VERSION=v7.5.1

# Base stage for reuse
FROM ubuntu:${UBUNTU_VERSION} AS base
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -qq update && \
    apt-get -qq install -y git curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

# Build libpsl-native using base
FROM base AS native
ARG POWERSHELL_NATIVE_VERSION=v7.4.0
ARG TARGETARCH

RUN apt-get -qq update && \
    apt-get -qq install -y cmake g++ gcc libicu-dev make patch unzip && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY patch/powershell-native-${POWERSHELL_NATIVE_VERSION}.patch /tmp/
WORKDIR /

RUN git clone https://github.com/PowerShell/PowerShell-Native.git /PowerShell-Native && \
    cd /PowerShell-Native && \
    git checkout tags/${POWERSHELL_NATIVE_VERSION} -b ${TARGETARCH} && \
    git apply /tmp/powershell-native-${POWERSHELL_NATIVE_VERSION}.patch && \
    git submodule update --init && \
    cd src/libpsl-native && \
    cmake -DCMAKE_BUILD_TYPE=Debug . && \
    make && \
    (make test || cat Testing/Temporary/LastTest.log || true)

# Build and package PowerShell
FROM base AS build_and_package
ARG POWERSHELL_VERSION
ARG TARGETARCH

RUN apt-get -qq update && \
    apt-get -qq install -y sudo libicu-dev unzip python3 python3-pip python3-typer && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=native /PowerShell-Native/src/powershell-unix/libpsl-native.so /usr/lib/

    COPY patch/powershell-${TARGETARCH}-${POWERSHELL_VERSION}.patch /tmp/powershell.patch
COPY patch/powershell-gen-${POWERSHELL_VERSION}.tar.gz /tmp/
COPY update-dotnet-sdk-and-tfm.sh /tmp/
COPY dotnet-install.py /tmp/

RUN chmod +x /tmp/update-dotnet-sdk-and-tfm.sh && \
    git clone https://github.com/PowerShell/PowerShell.git /PowerShell && \
    cd /PowerShell && \
    git checkout tags/${POWERSHELL_VERSION} -b ${TARGETARCH}-${POWERSHELL_VERSION} && \
    SDK_VERSION=$(python3 -c "import json; print(json.load(open('global.json'))['sdk']['version'])") && \
    python3 /tmp/dotnet-install.py --tag $SDK_VERSION && \
    ln -s /usr/share/dotnet/dotnet /usr/bin/dotnet && \
    git apply /tmp/powershell.patch && \
    cp /tmp/update-dotnet-sdk-and-tfm.sh . && \
    ./update-dotnet-sdk-and-tfm.sh -g && \
    tar -xzf /tmp/powershell-gen-${POWERSHELL_VERSION}.tar.gz -C .

RUN cd /PowerShell/src/powershell-unix && \
    dotnet restore --source https://api.nuget.org/v3/index.json && \
    dotnet publish . \
      -p:GenerateFullPaths=true \
      -p:ErrorOnDuplicatePublishOutputFiles=false \
      -p:IsWindows=false \
      -p:PublishReadyToRun=false \
      -p:WarnAsError=false \
      -p:RunAnalyzers=false \
      -p:SDKToUse=Microsoft.NET.Sdk \
      --self-contained \
      --configuration Release \
      --framework net$(dotnet --version | cut -d. -f1,2) \
      --runtime linux-$(uname -m) && \
    ln -sf /PowerShell/src/powershell-unix/bin/Release/net*/linux-*/publish/pwsh /usr/bin/pwsh && \
    cd /PowerShell && \
    
    pwsh -Command " \
        Set-Location /PowerShell; \
        Import-Module ./build.psm1 -ArgumentList \$true; \
        Import-Module ./tools/packaging/packaging.psm1; \
        Start-PSBootstrap -Scenario Package; \
        Start-PSBuild -Clean -PSModuleRestore -Runtime linux-${TARGETARCH} -Configuration Release -UseNuGetOrg; \
        Start-PSBuild -UseNuGetOrg -Configuration Release; \
        Start-PSPackage -Type deb -Version \"${POWERSHELL_VERSION#v}\" \
    " && \
    DEB_ARCH=$(dpkg --print-architecture) && \
    mkdir -p /tmp/artifacts && \
    cp /PowerShell/powershell_${POWERSHELL_VERSION#v}-1.deb_${DEB_ARCH}.deb /tmp/artifacts/

# Final runtime image
FROM ubuntu:${UBUNTU_VERSION} AS final
ARG POWERSHELL_VERSION
ARG TARGETARCH
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get -qq update && \
    apt-get -qq install -y --no-install-recommends curl ca-certificates && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY --from=build_and_package /usr/lib/libpsl-native.so /usr/lib/
COPY --from=build_and_package /tmp/artifacts/powershell_*.deb /tmp/powershell.deb

RUN apt-get update && \
    apt-get install -y /tmp/powershell.deb && \
    rm /tmp/powershell.deb

# Create a non-root user for security
RUN groupadd --system pwsh && \
    useradd --system --gid pwsh --create-home --shell /bin/bash pwsh

ENV PATH="${PATH}:/usr/bin"
RUN pwsh --version

# Switch to non-root user
USER pwsh
WORKDIR /home/pwsh

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 CMD pwsh -Command "exit 0" || exit 1

CMD ["/bin/bash"]
