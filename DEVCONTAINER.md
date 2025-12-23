# Development Container (DevContainer)

This repository includes a VS Code devcontainer configuration that prepares a development environment with pyenv and Python 3.11.13.

## Features
- Ubuntu 24.04 base image
- Installs `pyenv` and builds Python 3.11.13
- Creates a `.venv` virtual environment and runs `setup.sh` to install project requirements
- Adds recommended VS Code extensions and Python settings

## Usage
1. Open the repository in VS Code and choose "Reopen in Container" when prompted, or run **Remote-Containers: Reopen in Container**.
2. The container build will install pyenv and Python 3.11.13, then run the post-create script to set up `.venv` and install requirements.

## Notes
- Building Python via `pyenv` can take several minutes inside the container.
- If you prefer not to build Python inside the container, you can preinstall it on the host and forward to the container, or adjust `Dockerfile` to use a prebuilt image with Python.
- For macOS-like development, we provide `pyenv` and Python 3.11.13 to match the requested runtime.