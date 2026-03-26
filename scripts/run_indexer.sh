#!/bin/bash
# YeyoOS — run_indexer.sh
# Indexa el proyecto archivo por archivo para evitar OOM.
# Uso: bash scripts/run_indexer.sh

set -e
cd "$(dirname "$0")/.."

PYTHON=python3.11
SCRIPT=scripts/index_project.py

echo "🔍 YeyoOS ProjectIndexer (modo seguro — 1 archivo a la vez)"
echo ""

# Función para indexar un archivo
index_file() {
    local file="$1"
    $PYTHON "$SCRIPT" --file "$file" 2>&1 | grep -v "^INFO" || true
    $PYTHON "$SCRIPT" --file "$file" 2>/dev/null | sed 's/INFO  //'
}

# docs/
echo "📁 docs/"
for f in docs/*.md docs/archived/*.md; do
    [ -f "$f" ] || continue
    $PYTHON "$SCRIPT" --file "$f" 2>/dev/null | sed 's/INFO  //'
done

# prompts/ (hay muchos, los agrupamos)
echo ""
echo "📁 prompts/"
for f in prompts/capa0/*.md prompts/capa1/*.md prompts/capa2/*.md \
          prompts/capa3/*.md prompts/capa4/*.md prompts/capa5/*.md \
          prompts/capa6/*.md prompts/capa7/*.md; do
    [ -f "$f" ] || continue
    $PYTHON "$SCRIPT" --file "$f" 2>/dev/null | sed 's/INFO  //'
done

# db/
echo ""
echo "📁 db/migrations/"
for f in db/migrations/*.sql; do
    [ -f "$f" ] || continue
    $PYTHON "$SCRIPT" --file "$f" 2>/dev/null | sed 's/INFO  //'
done

# src/ (solo archivos clave, no tests)
echo ""
echo "📁 src/"
for f in $(find src -name "*.py" \
    ! -path "*/\__pycache__/*" \
    ! -name "__init__.py" \
    ! -path "*/tests/*" \
    | sort); do
    [ -f "$f" ] || continue
    $PYTHON "$SCRIPT" --file "$f" 2>/dev/null | sed 's/INFO  //'
done

echo ""
echo "📊 Stats finales:"
$PYTHON "$SCRIPT" --stats 2>/dev/null | sed 's/INFO  //'
