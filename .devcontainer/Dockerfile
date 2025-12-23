# Devcontainer Dockerfile for System project
# Use Microsoft base devcontainer image (Ubuntu) to be consistent with Codespaces
FROM mcr.microsoft.com/devcontainers/base:ubuntu

ENV DEBIAN_FRONTEND=noninteractive
ENV PYENV_ROOT=/home/vscode/.pyenv
ENV PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"

# Install system deps for building Python and common tooling
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git ca-certificates wget tzdata locales \
    libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev \
    libffi-dev liblzma-dev libncurses5-dev libncursesw5-dev libgdbm-dev \
    libnss3-dev libxml2-dev libxmlsec1-dev pkg-config xz-utils python3-venv \
    make gcc g++ unzip pkg-config libexpat1-dev \
    sox ffmpeg sudo && rm -rf /var/lib/apt/lists/*

# Create vscode user (UID/GID consistent with common devcontainer images)
RUN useradd -m -s /bin/bash vscode || true && \
    mkdir -p /workspace && chown -R vscode:vscode /workspace

# Install pyenv (as vscode user)
USER vscode
WORKDIR /home/vscode
RUN git clone https://github.com/pyenv/pyenv.git "$PYENV_ROOT" || true

# Ensure pyenv is initialized for all shells
USER root
RUN echo 'export PYENV_ROOT="$PYENV_ROOT"' > /etc/profile.d/pyenv.sh && \
    echo 'export PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"' >> /etc/profile.d/pyenv.sh && \
    echo 'eval "$(pyenv init -)"' >> /etc/profile.d/pyenv.sh && \
    chmod +x /etc/profile.d/pyenv.sh

# Install Python 3.11.13 via pyenv and set as global (as vscode user so files are owned)
USER vscode
ENV HOME=/home/vscode
SHELL ["/bin/bash", "-lc"]
RUN export PYENV_ROOT="$PYENV_ROOT" && \
    export PATH="$PYENV_ROOT/bin:$PATH" && \
    pyenv install -s 3.11.13 && \
    pyenv global 3.11.13 && \
    python -m pip install --upgrade pip setuptools wheel

# Copy repository into the container workspace
USER root
WORKDIR /workspace
COPY --chown=vscode:vscode .. /workspace

# Install project requirements (best-effort at build time)
USER vscode
SHELL ["/bin/bash", "-lc"]
RUN export PYENV_ROOT="$PYENV_ROOT" && export PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH" && \
    pyenv rehash || true && \
    if [ -f /workspace/requirements.txt ]; then pip install -r /workspace/requirements.txt || true; fi

# Default user and workdir
USER vscode
WORKDIR /workspace

CMD ["/bin/bash"]
