#!/bin/bash
# YeyoOS — Ejecutar todos los tests de Capa 2
# Uso: bash scripts/test_capa2.sh

set -e

echo "🧠 YeyoOS — Tests Capa 2: Cerebro"
echo "=================================="

cd ~/yeyo-os
source .venv/bin/activate

echo ""
echo "📋 Tests unitarios..."
python -m pytest tests/unit/ -v --tb=short 2>&1 | tail -20

echo ""
echo "📋 Tests de integración..."
python -m pytest tests/integration/ -v --tb=short -m integration 2>&1 | tail -30

echo ""
echo "📋 Tests de Capa 2 completos..."
python -m pytest tests/integration/capa2/ -v --tb=short -m integration 2>&1

echo ""
echo "📊 Resumen completo..."
python -m pytest tests/ -v --tb=line 2>&1 | tail -10

echo ""
echo "🧠 Tests Capa 2 completados"
