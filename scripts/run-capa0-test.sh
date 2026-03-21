#!/bin/bash
source /home/yeyo/yeyo-venv/bin/activate
cd /mnt/c/Users/yeyoa/Desktop/yeyo-os
python -m pytest tests/test_capa0_integration.py -v --tb=short 2>&1
echo "=== 0.12 DONE ==="