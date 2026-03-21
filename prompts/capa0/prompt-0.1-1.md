## ═══════════════════════════════════════
## MICRO-FASE 0.1 — Kernel Headers y Módulos
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.1-1 [CLI] — Instalar kernel headers y verificar módulos

```
Estamos construyendo YeyoOS. Micro-fase 0.1: instalar kernel headers necesarios para compilar drivers y módulos.

Entorno: WSL2 Ubuntu. Micro-fase 0.0 (Btrfs) completada.

EJECUTAR:
1. Instalar kernel headers y herramientas de compilación:
   sudo apt update
   sudo apt install -y linux-headers-$(uname -r) build-essential dkms
   sudo apt install -y pkg-config libssl-dev libffi-dev

2. Verificar módulos cargados necesarios:
   lsmod | grep -E "btrfs|nvidia|overlay"

3. Instalar herramientas de diagnóstico:
   sudo apt install -y htop iotop sysstat curl wget git

VERIFICAR:
- [ ] Headers instalados: `ls /usr/src/linux-headers-$(uname -r)` → directorio existe
- [ ] GCC funciona: `gcc --version` → versión
- [ ] Make funciona: `make --version` → versión
- [ ] DKMS instalado: `dkms status` → sin error
- [ ] Git instalado: `git --version` → versión

SI FALLA:
- Headers no match kernel: `apt search linux-headers` → buscar versión correcta
- En WSL2 los headers pueden ser especiales: `apt install linux-headers-generic`

GATE: gcc + make + dkms funcionando, headers instalados para el kernel actual.
```
