# Home Assistant Custom Integration Development Container
# Python 3.13 required for Home Assistant as of Nov 2025
# Reference: https://developers.home-assistant.io/docs/development_environment/

FROM mcr.microsoft.com/devcontainers/python:3.14

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    SHELL=/usr/bin/zsh

# Declare TARGETARCH for multi-arch builds (automatically set by buildx)
ARG TARGETARCH

# Install system dependencies required by Home Assistant and media processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build essentials
    build-essential \
    cmake \
    autoconf \
    pkg-config \
    # Media processing (required for media_player components)
    ffmpeg \
    libturbojpeg0 \
    libturbojpeg0-dev \
    # FFmpeg development libraries (required for av/PyAV package - stream component)
    libavformat-dev \
    libavcodec-dev \
    libavdevice-dev \
    libavutil-dev \
    libavfilter-dev \
    libswscale-dev \
    libswresample-dev \
    # Network capture (useful for debugging)
    libpcap-dev \
    # Bluetooth support
    libbluetooth-dev \
    # Additional tools
    curl \
    wget \
    jq \
    # Shell enhancements
    zsh \
    fzf \
    # Clean up
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install go2rtc binary for the target architecture
# Version should match what Home Assistant expects (check HA's Dockerfile)
ARG GO2RTC_VERSION=v1.9.12
RUN set -eux; \
    case "${TARGETARCH}" in \
        amd64) GO2RTC_SUFFIX='amd64' ;; \
        arm64) GO2RTC_SUFFIX='arm64' ;; \
        arm) GO2RTC_SUFFIX='arm' ;; \
        *) echo "Unsupported architecture: ${TARGETARCH}" && exit 1 ;; \
    esac; \
    curl -fsSL "https://github.com/AlexxIT/go2rtc/releases/download/${GO2RTC_VERSION}/go2rtc_linux_${GO2RTC_SUFFIX}" -o /bin/go2rtc \
    && chmod +x /bin/go2rtc \
    && /bin/go2rtc --version

# Note: Config directory is created at /workspaces/homeassistant-zowietek/config (gitignored)
# by postCreateCommand.sh - no need to create here as it's within the mounted workspace

# Switch to vscode user for remaining setup
USER vscode

# Create virtual environment for Home Assistant development
ENV HA_VENV=/home/vscode/.local/ha-venv
RUN python -m venv ${HA_VENV}

# Install Home Assistant and development dependencies in venv
RUN ${HA_VENV}/bin/pip install --upgrade pip setuptools wheel && \
    ${HA_VENV}/bin/pip install \
    homeassistant \
    pytest \
    pytest-asyncio \
    pytest-cov \
    pytest-homeassistant-custom-component \
    ruff \
    mypy \
    pre-commit

# Set up Oh My Zsh for better terminal experience
RUN sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)" "" --unattended || true

# Add useful aliases and PATH configuration
RUN echo '\n# Home Assistant Development\n\
export PATH="${HA_VENV}/bin:$PATH"\n\
alias ha="hass -c /workspaces/homeassistant-zowietek/config"\n\
alias halog="tail -f /workspaces/homeassistant-zowietek/config/home-assistant.log"\n\
alias pytest="python -m pytest"\n\
alias ruff-check="ruff check ."\n\
alias ruff-fix="ruff check --fix ."\n\
\n# uv configuration\n\
export UV_LINK_MODE=copy\n\
' >> /home/vscode/.zshrc

# Add to bashrc as fallback
RUN echo '\n# Home Assistant Development\n\
export PATH="${HA_VENV}/bin:$PATH"\n\
alias ha="hass -c /workspaces/homeassistant-zowietek/config"\n\
alias halog="tail -f /workspaces/homeassistant-zowietek/config/home-assistant.log"\n\
alias pytest="python -m pytest"\n\
export UV_LINK_MODE=copy\n\
' >> /home/vscode/.bashrc

# Set working directory
WORKDIR /workspaces

# Default command
CMD ["sleep", "infinity"]
