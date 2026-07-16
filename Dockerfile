# Shared setup stage ###########################################################
# Use fedora for arm/mac and x86 building
FROM fedora:38 AS common

ENV PATH=/odin/bin:/odin/scripts:/venv/bin:$PATH

# Get fundamental packages
RUN --mount=type=cache,target=/var/cache/dnf,sharing=locked \
    dnf update -y && \
    dnf install -y curl \
    tar ca-certificates librdkafka-devel --setopt=install_weak_deps=False 

# Get zellij
RUN curl -L https://github.com/zellij-org/zellij/releases/download/v0.40.1/zellij-x86_64-unknown-linux-musl.tar.gz -o zellij.tar.gz && \
    tar -xvf zellij.tar.gz -C /usr/bin && \
    rm zellij.tar.gz
RUN mkdir -p ~/.config/zellij && \
    zellij setup --dump-config > ~/.config/zellij/config.kdl

# Developer stage for devcontainer #############################################
FROM common AS developer

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# System dependencies
RUN --mount=type=cache,target=/var/cache/dnf,sharing=locked \
    dnf update -y && dnf install -y \
    # General build
    @development-tools gcc g++ cmake git ccache \
    # odin-data C++ dependencies
    blosc-devel boost-devel hdf5-devel log4cxx-devel libpcap-devel czmq-devel \
    # python
    python3.11-devel python3.11-libs \
    # clang tools
    clang-tools-extra \
    # debugging
    gdb valgrind --setopt=install_weak_deps=False 
    # tidy up

ENV CCACHE_DIR=/root/.cache/ccache

# Python dependencies

ENV PATH="/venv/bin:$PATH"
ENV UV_LINK_MODE=copy
ENV UV_COMPILE_BYTECODE=1

RUN uv venv /venv
    

RUN --mount=type=cache,target=/root/.cache/uv \
    uv pip install --python /venv/bin/python git+https://github.com/odin-detector/odin-control@1cf475b60abf66666d31c7e74b9d19540c2ea6c3

# Install hdf5filters from source
COPY . /odin
WORKDIR /odin
RUN --mount=type=cache,target=/app/hdf5filters/cmake-build \
    --mount=type=cache,target=/root/.cache/ccache \
    cd hdf5filters && \
    mkdir -p cmake-build && cd cmake-build && \
    cmake   -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
            -DCMAKE_C_COMPILER_LAUNCHER=ccache \
            -DCMAKE_INSTALL_PREFIX=/odin \
            -DCMAKE_BUILD_TYPE=Release .. && \
    make -j$(nproc) VERBOSE=1 && \
    make install
    #rm -rf hdf5filters


# Copy in project
WORKDIR /odin/odin-data

# C++
RUN --mount=type=cache,target=/app/build/build \
    --mount=type=cache,target=/root/.cache/ccache \
    mkdir -p build && cd build && \
    cmake   -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
            -DCMAKE_C_COMPILER_LAUNCHER=ccache \
            -DCMAKE_INSTALL_PREFIX=/odin \
            -DODINDATA_ROOT_DIR=/odin ../cpp && \
    make -j$(nproc) VERBOSE=1 && \
    make install

# Python
WORKDIR /odin/odin-data/python
RUN uv pip install --python /venv/bin/python '.[meta_writer]'

# tickit-devices install# On macOS and Linux.

RUN --mount=type=cache,target=/var/cache/dnf,sharing=locked \
    dnf install -y graphviz 

WORKDIR /odin/tickit-devices

RUN --mount=type=cache,target=/root/.cache/uv \ 
    uv sync --locked --no-editable --no-dev     

# eiger-detector build

WORKDIR /odin/eiger-detector
RUN --mount=type=cache,target=/odin/eiger-detector/build \
    --mount=type=cache,target=/root/.cache/ccache \
    mkdir -p build && cd build && \
    cmake   -DCMAKE_CXX_COMPILER_LAUNCHER=ccache \
            -DCMAKE_C_COMPILER_LAUNCHER=ccache \
            -DCMAKE_INSTALL_PREFIX=/odin \
            -DODINDATA_ROOT_DIR=/odin \
            ../cpp && \
    make -j$(nproc) VERBOSE=1 && \
    make install

WORKDIR /odin/eiger-detector/python
RUN uv pip install --python /venv/bin/python '.[dev,sim]' 
WORKDIR /odin/odin-data
RUN uv pip install --python /venv/bin/python $([ -f dev-requirements.txt ] && echo '-c dev-requirements.txt') -e './python[dev]'

#fastcs-eiger build
WORKDIR /odin/fastcs-eiger
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable --no-dev


# Build stage - throwaway stage for runtime assets #############################
FROM developer AS build

FROM build AS debug

RUN uv pip install debugpy \
    uv pip install -e .



# Runtime stage ################################################################
FROM common AS runtime

# Runtime system dependencies
RUN --mount=type=cache,target=/var/cache/dnf,sharing=locked \
    dnf update -y && dnf install -y \
    # C++ dependencies
    blosc-devel boost-devel hdf5-devel log4cxx-devel libpcap-devel czmq-devel \
    # Python dependencies
    python3.11 --setopt=install_weak_deps=False 


COPY --from=build /odin /odin
COPY --from=build /venv /venv
COPY eiger-detector/deploy /odin/eiger-deploy

RUN rm -rf /odin/odin-data /odin/odin-control

WORKDIR /odin

