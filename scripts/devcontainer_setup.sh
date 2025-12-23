#!/usr/bin/env bash
set -euo pipefail

# Devcontainer post-create setup script
# - Ensures pyenv is available in the current shell
# - Installs Python 3.11.13 via pyenv if missing
# - Creates .venv with the installed Python and runs project setup

export PYENV_ROOT="/home/vscode/.pyenv"
export PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"

# Load pyenv init if available
if command -v pyenv &> /dev/null; then
  eval "$(pyenv init -)" || true
else
  echo "Warning: pyenv not found in PATH. Something went wrong with Dockerfile install."
fi

PY_VERSION=3.11.13

if ! pyenv versions --bare | grep -q "^${PY_VERSION}$"; then
  echo "Installing Python ${PY_VERSION} via pyenv..."
  pyenv install -s ${PY_VERSION}
fi

pyenv global ${PY_VERSION}

echo "Creating virtual environment .venv with Python $(python --version)"
python -m venv .venv
source .venv/bin/activate

# Upgrade pip
pip install --upgrade pip setuptools wheel

# Run the project's setup script (which will install requirements)
if [ -f "/workspace/setup.sh" ]; then
  bash /workspace/setup.sh
else
  echo "setup.sh not found; installing requirements directly"
  pip install -r /workspace/requirements.txt
fi

echo "Devcontainer post-create setup completed. Activate with: source .venv/bin/activate"