## ═══════════════════════════════════════
## MICRO-FASE 0.0 — Particiones Btrfs
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.0-1 [CLI] — Crear estructura Btrfs con subvolumes

```
Estamos construyendo YeyoOS, un OS AI-nativo. Esta es la micro-fase 0.0: crear la estructura de particiones Btrfs.

Entorno: WSL2 Ubuntu sobre Windows, GTX 1060 3GB, 16GB RAM. Estamos en desarrollo, NO en hardware real aún. Necesitamos simular la estructura Btrfs que usará el OS final.

EJECUTAR:
1. Crear un archivo de imagen de 20GB para simular el disco:
   - `dd if=/dev/zero of=/tmp/yeyo-disk.img bs=1M count=20480`
   - `mkfs.btrfs /tmp/yeyo-disk.img`

2. Montar y crear los 5 subvolumes:
   - `sudo mkdir -p /mnt/yeyo`
   - `sudo mount /tmp/yeyo-disk.img /mnt/yeyo`
   - `sudo btrfs subvolume create /mnt/yeyo/@root`
   - `sudo btrfs subvolume create /mnt/yeyo/@home`
   - `sudo btrfs subvolume create /mnt/yeyo/@yeyo-data`
   - `sudo btrfs subvolume create /mnt/yeyo/@flash-memory`
   - `sudo btrfs subvolume create /mnt/yeyo/@snapshots`

3. Verificar la estructura:
   - `sudo btrfs subvolume list /mnt/yeyo`

4. Crear directorios base dentro de @yeyo-data:
   - `sudo mkdir -p /mnt/yeyo/@yeyo-data/{config,models,packages,logs}`
   - `sudo mkdir -p /mnt/yeyo/@flash-memory/{hot,warm,cold}`

5. Desmontar (lo montaremos cuando sea necesario):
   - `sudo umount /mnt/yeyo`

VERIFICAR:
- [ ] Archivo de imagen existe: `ls -lh /tmp/yeyo-disk.img` → ~20GB
- [ ] 5 subvolumes creados: `sudo mount /tmp/yeyo-disk.img /mnt/yeyo && sudo btrfs subvolume list /mnt/yeyo` → 5 líneas
- [ ] Directorios base existen en @yeyo-data y @flash-memory
- [ ] Btrfs tools instalados: `btrfs --version`

SI FALLA:
- btrfs no instalado: `sudo apt install -y btrfs-progs`
- Espacio insuficiente en /tmp: usar otro path como ~/yeyo-disk.img
- WSL2 no soporta btrfs: verificar kernel con `uname -r`, necesita 5.15+

GATE: 5 subvolumes listados correctamente + directorios internos existen.
```
