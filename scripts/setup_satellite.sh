#!/bin/bash
# ============================================================
# YeyoOS — Setup de PC Satélite
# Corre esto en cada nueva PC para configurarla
# ============================================================

echo "🌐 YeyoOS — Configuración de Satélite"
echo "========================================"
echo ""

# 1. Verificar dependencias
echo "📦 Verificando dependencias..."
command -v python3 >/dev/null 2>&1 || { echo "❌ python3 no encontrado. Instálalo primero."; exit 1; }
command -v psql >/dev/null 2>&1 || { echo "❌ PostgreSQL no encontrado. Instálalo primero."; exit 1; }
echo "✅ python3 y PostgreSQL encontrados"
echo ""

# 2. Crear DB local si no existe
echo "🗄️  Verificando base de datos local..."
if psql -lqt | cut -d \| -f 1 | grep -qw yeyoos; then
    echo "✅ Base de datos 'yeyoos' ya existe"
else
    echo "Creando base de datos 'yeyoos'..."
    createdb yeyoos
    echo "✅ Base de datos creada"
fi
echo ""

# 3. Correr migraciones
echo "📋 Corriendo migraciones..."
for f in db/migrations/*.sql; do
    echo "  → $f"
    psql -d yeyoos -f "$f" 2>/dev/null
done
echo "✅ Migraciones aplicadas"
echo ""

# 4. Importar memorias
echo "🧠 Importando memorias..."
if [ -f scripts/yeyoos_memories_export.sql ]; then
    psql -d yeyoos -f scripts/yeyoos_memories_export.sql 2>/dev/null
    COUNT=$(psql -d yeyoos -t -c "SELECT COUNT(*) FROM flash_memories;" 2>/dev/null | tr -d ' ')
    echo "✅ $COUNT memorias importadas"
else
    echo "⚠️  No se encontró export de memorias (scripts/yeyoos_memories_export.sql)"
fi
echo ""

# 5. Instalar dependencias Python
echo "🐍 Instalando dependencias..."
if [ -d .venv ]; then
    source .venv/bin/activate
else
    python3 -m venv .venv
    source .venv/bin/activate
fi
pip install -r requirements.txt -q
echo "✅ Dependencias instaladas"
echo ""

# 6. Configurar .env
echo "⚙️  Configuración de Cloud Sync (Supabase)"
echo "Necesitas la URL y Key de Supabase."
echo "(Pregúntale a Diego o revisa el dashboard de Supabase)"
echo ""

if [ -f .env ] && grep -q "SUPABASE_URL" .env; then
    echo "✅ .env ya tiene configuración de Supabase"
else
    read -p "SUPABASE_URL (ej: https://xxx.supabase.co): " SUPA_URL
    read -p "SUPABASE_KEY (la anon key, empieza con eyJ...): " SUPA_KEY
    
    echo "" >> .env
    echo "# Cloud Memory Sync (Supabase)" >> .env
    echo "SUPABASE_URL=$SUPA_URL" >> .env
    echo "SUPABASE_KEY=$SUPA_KEY" >> .env
    echo "✅ .env configurado"
fi
echo ""

# 7. Verificar conexión
echo "🔗 Verificando conexión a Supabase..."
source .venv/bin/activate
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
import httpx
url = os.getenv('SUPABASE_URL','')
key = os.getenv('SUPABASE_KEY','')
if not url or not key:
    print('❌ SUPABASE_URL o SUPABASE_KEY no configurados')
    exit(1)
r = httpx.get(f'{url}/rest/v1/cloud_memories?select=id&limit=1',
    headers={'apikey': key, 'Authorization': f'Bearer {key}'})
if r.status_code == 200:
    print(f'✅ Conectado a Supabase — memorias en cloud disponibles')
else:
    print(f'❌ Error: {r.status_code} — {r.text[:100]}')
" 2>/dev/null
echo ""

echo "========================================"
echo "🎉 ¡Setup completo!"
echo ""
echo "Para iniciar YeyoOS:"
echo "  source .venv/bin/activate"
echo "  python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
echo ""
echo "Las memorias se sincronizarán automáticamente via cloud ☁️"
