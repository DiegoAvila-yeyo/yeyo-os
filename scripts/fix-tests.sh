#!/bin/bash
source /home/yeyo/yeyo-venv/bin/activate
source /home/yeyo/.cargo/env
export NVM_DIR="/home/yeyo/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# Fix rustup default
su - yeyo -c "source ~/.cargo/env && rustup default stable" 2>/dev/null || true

cd /mnt/c/Users/yeyoa/Desktop/yeyo-os
python -m pytest tests/test_capa0_integration.py::test_rust_installed \
                 tests/test_capa0_integration.py::test_rust_workspace_builds \
                 tests/test_capa0_integration.py::test_podman_rootless -v 2>&1