FROM python:3.10-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    bash \
    jq \
    git \
    cmake \
    build-essential \
    # OpenCV runtime dependencies (for non-headless fallback)
    libgl1-mesa-glx \
    libglib2.0-0 \
    libxcb1 \
    libx11-6 \
    && rm -rf /var/lib/apt/lists/*

# Download and install opencode (glibc build for arm64)
ARG OPENCODE_VERSION=latest
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "aarch64" ] || [ "$ARCH" = "arm64" ]; then \
        ASSET_NAME="opencode-linux-arm64.tar.gz"; \
    else \
        ASSET_NAME="opencode-linux-x64.tar.gz"; \
    fi && \
    echo "Downloading opencode $ASSET_NAME..." && \
    curl -sL "https://github.com/anomalyco/opencode/releases/latest/download/$ASSET_NAME" | tar xz -C /usr/local/bin && \
    chmod +x /usr/local/bin/opencode

# Install uv for Python venv management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Create workspace directories
WORKDIR /workspace
RUN mkdir -p /output /inputs

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
