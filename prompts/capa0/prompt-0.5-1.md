## ═══════════════════════════════════════
## MICRO-FASE 0.5 — Node.js 20 + Scaffold
## Tipo: MIXTA | Prompts: 2 (1 CLI + 1 VSCODE)
## ═══════════════════════════════════════

### PROMPT 0.5-1 [CLI] — Instalar Node.js 20 LTS

```
Estamos construyendo YeyoOS. Micro-fase 0.5, Prompt 1 de 2: instalar Node.js 20 LTS para el frontend (Next.js).

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.4 completadas.

EJECUTAR:
1. Instalar Node.js 20 via nvm (más flexible que apt):
   curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.7/install.sh | bash
   export NVM_DIR="$HOME/.nvm"
   [ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
   nvm install 20
   nvm use 20
   nvm alias default 20

2. Verificar npm y instalar pnpm (más rápido que npm):
   npm install -g pnpm

3. Agregar a .env:
   # Node.js
   NODE_ENV=development

VERIFICAR:
- [ ] Node version: `node --version` → v20.x.x
- [ ] npm version: `npm --version` → 10.x.x
- [ ] pnpm version: `pnpm --version` → 8.x o 9.x
- [ ] nvm funciona: `nvm list` → v20.x como default

SI FALLA:
- nvm no carga: agregar a ~/.bashrc las líneas de export NVM_DIR
- Permisos: no usar sudo con nvm

GATE: Node.js 20 LTS instalado via nvm, pnpm disponible.
```
