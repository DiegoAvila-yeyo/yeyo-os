## ═══════════════════════════════════════
## MICRO-FASE 0.9 — Podman (Containers)
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.9-1 [CLI] — Instalar Podman para containers de nodos

```
Estamos construyendo YeyoOS. Micro-fase 0.9: instalar Podman como runtime de containers (reemplazo de Docker, más seguro).

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.8 completadas.

IMPORTANTE: Usamos Podman, NO Docker. Podman es rootless por defecto (más seguro) y compatible con Docker CLI.

EJECUTAR:
1. Instalar Podman:
   sudo apt install -y podman

2. Configurar Podman rootless:
   podman system migrate

3. Verificar que funciona:
   podman run --rm alpine echo "YeyoOS container OK"

4. Configurar registries:
   mkdir -p ~/.config/containers
   Crear ~/.config/containers/registries.conf:
   [registries.search]
   registries = ['docker.io']

5. Crear un container de test para verificar aislamiento:
   podman run --rm -it --security-opt=no-new-privileges:true \
     --cap-drop=ALL \
     alpine sh -c "whoami && id && echo 'Isolated OK'"
   → Debe mostrar usuario non-root

6. Verificar que Podman no expone socket peligroso:
   ls /var/run/docker.sock 2>/dev/null && echo "PELIGRO: Docker socket existe" || echo "OK: No docker socket"

VERIFICAR:
- [ ] Podman version: `podman --version` → 3.x o 4.x
- [ ] Rootless funciona: `podman info | grep rootless` → true
- [ ] Container corre: `podman run --rm alpine echo test` → "test"
- [ ] No Docker socket: `ls /var/run/docker.sock 2>/dev/null` → no existe
- [ ] Capabilities dropped: `podman run --rm --cap-drop=ALL alpine cat /proc/1/status | grep Cap` → CapEff: 0

SI FALLA:
- Podman no instala: `sudo apt update && sudo apt install -y podman`
- Rootless falla: `podman system reset` y reintentar
- cgroup v2 necesario: verificar `cat /sys/fs/cgroup/cgroup.controllers`

NO HACER:
- NO instalar Docker (usamos Podman)
- NO montar /var/run/docker.sock en ningún container JAMÁS
- NO correr containers como root

GATE: Podman rootless funcionando, containers corren sin root, no hay Docker socket.
```
