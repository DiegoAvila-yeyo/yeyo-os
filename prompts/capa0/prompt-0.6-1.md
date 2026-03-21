## ═══════════════════════════════════════
## MICRO-FASE 0.6 — Python 3.11 + Virtual Environment
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.6-1 [CLI] — Instalar Python 3.11 y configurar venv

```
Estamos construyendo YeyoOS. Micro-fase 0.6: Python 3.11 como backend de IA y Flash Memory.

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.5 completadas.

EJECUTAR:
1. Instalar Python 3.11:
   sudo apt install -y python3.11 python3.11-venv python3.11-dev python3-pip

2. Crear virtual environment para el proyecto:
   cd ~/yeyo-os
   python3.11 -m venv .venv
   source .venv/bin/activate

3. Instalar dependencias base:
   pip install --upgrade pip
   pip install asyncpg redis aiohttp
   pip install python-dotenv
   pip install pydantic
   pip install sentence-transformers
   pip install pytest pytest-asyncio httpx

4. Crear requirements.txt:
   pip freeze > requirements.txt

5. Crear estructura de carpetas Python:
   mkdir -p src/{memory,ia,api,utils}
   touch src/__init__.py src/memory/__init__.py src/ia/__init__.py src/api/__init__.py src/utils/__init__.py

6. Crear src/utils/config.py:
   # YeyoOS Configuration — Micro-fase 0.6
   from dotenv import load_dotenv
   import os
   
   load_dotenv()
   
   DATABASE_URL = os.getenv("DATABASE_URL")
   TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
   REDIS_URL = os.getenv("REDIS_URL")
   NODE_ENV = os.getenv("NODE_ENV", "development")

7. Crear test básico tests/test_config.py:
   mkdir -p tests
   touch tests/__init__.py
   # test que verifica que config carga las variables

8. Agregar .venv a .gitignore:
   echo ".venv" >> .gitignore

VERIFICAR:
- [ ] Python version: `python --version` → 3.11.x (dentro del venv)
- [ ] Venv activo: `which python` → ~/yeyo-os/.venv/bin/python
- [ ] asyncpg importa: `python -c "import asyncpg; print('OK')"` → OK
- [ ] sentence-transformers importa: `python -c "from sentence_transformers import SentenceTransformer; print('OK')"` → OK
- [ ] Config carga .env: `python -c "from src.utils.config import DATABASE_URL; print(DATABASE_URL)"` → postgresql://...
- [ ] pytest funciona: `pytest tests/ -v` → pass
- [ ] .venv en .gitignore: `grep '.venv' .gitignore` → match

SI FALLA:
- Python 3.11 no disponible: `sudo add-apt-repository ppa:deadsnakes/ppa && sudo apt update`
- sentence-transformers falla: verificar que hay 2GB+ de RAM libre (descarga modelo)
- CUDA warning en sentence-transformers: ignorar, usamos CPU para embeddings

NO HACER:
- No instalar torch con CUDA aún (eso es 0.10 + Capa 7 para training)
- No crear lógica de negocio aún
- No hardcodear passwords (todo desde .env)

GATE: Python 3.11 en venv, todas las dependencias base instaladas, config.py carga .env correctamente, pytest funciona.
```
