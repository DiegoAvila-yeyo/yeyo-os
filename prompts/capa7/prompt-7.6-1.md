## ═══════════════════════════════════════
## MICRO-FASE 7.6 — ISO Builder
## Tipo: CLI | Prompts: 2 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.6-1 [CLI] — Crear sistema de generación de ISO bootable

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.6 (parte 1) de Capa 7 (Evolución): crear el sistema que genera una imagen ISO bootable de YeyoOS.

CONTEXTO:
- Capas 0-6 completadas + micro-fases 7.0-7.5
- ISO Builder genera yeyo-os-{version}.iso (~2-4GB)
- Base: Ubuntu minimal via debootstrap
- Capas: base system → YeyoOS packages → config → user data (opcional)
- Bootable: UEFI + Legacy BIOS via GRUB
- Herramientas: debootstrap, squashfs-tools, xorriso, grub-mkrescue
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre un terminal.

CREAR:

1. Crear estructura de directorios:
   mkdir -p scripts/iso
   mkdir -p tests/iso

2. Crear archivo scripts/iso/build_iso.sh:

   Ruta: ~/yeyo-os/scripts/iso/build_iso.sh
   Contenido:

   #!/bin/bash
   # ═══════════════════════════════════════
   # YeyoOS — ISO Builder
   # Micro-fase 7.6 — Capa 7: Evolución
   #
   # Genera imagen ISO bootable de YeyoOS.
   # Uso: sudo ./build_iso.sh [--version X.Y.Z] [--include-userdata]
   # ═══════════════════════════════════════

   set -euo pipefail

   # --- Configuración ---
   YEYO_VERSION="${YEYO_VERSION:-1.0.0}"
   BUILD_DIR="/tmp/yeyo-iso-build"
   OUTPUT_DIR="${OUTPUT_DIR:-./dist}"
   ROOTFS="${BUILD_DIR}/rootfs"
   ISO_DIR="${BUILD_DIR}/iso"
   ISO_NAME="yeyo-os-${YEYO_VERSION}.iso"
   INCLUDE_USERDATA=false
   UBUNTU_RELEASE="jammy"

   # --- Parsear argumentos ---
   while [[ $# -gt 0 ]]; do
       case $1 in
           --version) YEYO_VERSION="$2"; ISO_NAME="yeyo-os-${YEYO_VERSION}.iso"; shift 2 ;;
           --include-userdata) INCLUDE_USERDATA=true; shift ;;
           --output-dir) OUTPUT_DIR="$2"; shift 2 ;;
           *) echo "Argumento desconocido: $1"; exit 1 ;;
       esac
   done

   # --- Verificar root ---
   if [[ $EUID -ne 0 ]]; then
       echo "ERROR: Este script requiere privilegios root (sudo)"
       exit 1
   fi

   # --- Verificar dependencias ---
   DEPS="debootstrap mksquashfs xorriso grub-mkrescue"
   for dep in $DEPS; do
       if ! command -v "$dep" &>/dev/null; then
           echo "ERROR: $dep no encontrado. Instalar: apt install debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools"
           exit 1
       fi
   done

   echo "═══════════════════════════════════════"
   echo " YeyoOS ISO Builder v${YEYO_VERSION}"
   echo "═══════════════════════════════════════"
   echo "Build dir: ${BUILD_DIR}"
   echo "Output: ${OUTPUT_DIR}/${ISO_NAME}"
   echo "Include userdata: ${INCLUDE_USERDATA}"
   echo ""

   # --- Limpiar build anterior ---
   echo "[1/8] Limpiando build anterior..."
   rm -rf "${BUILD_DIR}"
   mkdir -p "${BUILD_DIR}" "${ROOTFS}" "${ISO_DIR}" "${OUTPUT_DIR}"

   # --- Paso 1: Bootstrap base system ---
   echo "[2/8] Bootstrap del sistema base (${UBUNTU_RELEASE})..."
   debootstrap --arch=amd64 --variant=minbase \
       --include=linux-image-generic,systemd,sudo,curl,wget,git,python3,python3-pip,python3-venv,postgresql,redis-server,btrfs-progs,nvidia-driver-535 \
       "${UBUNTU_RELEASE}" "${ROOTFS}" http://archive.ubuntu.com/ubuntu

   # --- Paso 2: Configurar sistema base ---
   echo "[3/8] Configurando sistema base..."
   cat > "${ROOTFS}/etc/hostname" <<EOF
   yeyo-os
   EOF

   cat > "${ROOTFS}/etc/hosts" <<EOF
   127.0.0.1   localhost
   127.0.1.1   yeyo-os
   EOF

   # Configurar locales
   chroot "${ROOTFS}" bash -c "
       apt-get update -qq
       apt-get install -y -qq locales
       locale-gen en_US.UTF-8 es_ES.UTF-8
       update-locale LANG=en_US.UTF-8
   "

   # Configurar fstab para Btrfs
   cat > "${ROOTFS}/etc/fstab" <<EOF
   # YeyoOS Btrfs layout
   # Configurado durante instalación por el wizard
   # /dev/sdX  /          btrfs  defaults,subvol=@         0  1
   # /dev/sdX  /home      btrfs  defaults,subvol=@home     0  2
   # /dev/sdX  /snapshots btrfs  defaults,subvol=@snapshots 0  2
   EOF

   # --- Paso 3: Instalar paquetes YeyoOS ---
   echo "[4/8] Instalando paquetes YeyoOS..."
   # Copiar código fuente de YeyoOS
   mkdir -p "${ROOTFS}/opt/yeyo-os"
   cp -r ~/yeyo-os/src "${ROOTFS}/opt/yeyo-os/"
   cp -r ~/yeyo-os/frontend "${ROOTFS}/opt/yeyo-os/" 2>/dev/null || true
   cp -r ~/yeyo-os/rust "${ROOTFS}/opt/yeyo-os/" 2>/dev/null || true
   cp ~/yeyo-os/requirements.txt "${ROOTFS}/opt/yeyo-os/" 2>/dev/null || true

   # Instalar dependencias Python
   chroot "${ROOTFS}" bash -c "
       python3 -m venv /opt/yeyo-os/.venv
       /opt/yeyo-os/.venv/bin/pip install --upgrade pip
       /opt/yeyo-os/.venv/bin/pip install -r /opt/yeyo-os/requirements.txt 2>/dev/null || true
   "

   # Instalar Ollama
   chroot "${ROOTFS}" bash -c "
       curl -fsSL https://ollama.ai/install.sh | sh
   "

   # --- Paso 4: Configurar servicios systemd ---
   echo "[5/8] Configurando servicios systemd..."

   # Servicio de Ollama
   cat > "${ROOTFS}/etc/systemd/system/ollama.service" <<EOF
   [Unit]
   Description=Ollama AI Server
   After=network.target

   [Service]
   Type=simple
   ExecStart=/usr/local/bin/ollama serve
   Restart=always
   RestartSec=3

   [Install]
   WantedBy=multi-user.target
   EOF

   # Servicio principal de YeyoOS
   cat > "${ROOTFS}/etc/systemd/system/yeyo-os.service" <<EOF
   [Unit]
   Description=YeyoOS Core Service
   After=network.target postgresql.service redis-server.service ollama.service
   Requires=postgresql.service redis-server.service

   [Service]
   Type=simple
   WorkingDirectory=/opt/yeyo-os
   ExecStart=/opt/yeyo-os/.venv/bin/python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   Restart=always
   RestartSec=5
   Environment=YEYO_ENV=production

   [Install]
   WantedBy=multi-user.target
   EOF

   # Guardian daemon
   cat > "${ROOTFS}/etc/systemd/system/yeyo-guardian.service" <<EOF
   [Unit]
   Description=YeyoOS Guardian Security Daemon
   Before=yeyo-os.service
   After=network.target

   [Service]
   Type=simple
   ExecStart=/opt/yeyo-os/rust/guardian/target/release/yeyo-guardian
   Restart=always
   RestartSec=1
   Priority=-20

   [Install]
   WantedBy=multi-user.target
   EOF

   chroot "${ROOTFS}" bash -c "
       systemctl enable ollama.service
       systemctl enable yeyo-os.service
       systemctl enable yeyo-guardian.service
       systemctl enable postgresql.service
       systemctl enable redis-server.service
   "

   # --- Paso 5: Configurar primer boot (Installation Wizard) ---
   echo "[6/8] Configurando wizard de primer boot..."
   cat > "${ROOTFS}/opt/yeyo-os/first-boot.sh" <<'EOF'
   #!/bin/bash
   # YeyoOS First Boot Script
   # Ejecuta el Installation Wizard en primer inicio

   FIRST_BOOT_FLAG="/opt/yeyo-os/.first-boot-done"

   if [ ! -f "$FIRST_BOOT_FLAG" ]; then
       echo "═══════════════════════════════════════"
       echo " Bienvenido a YeyoOS — Primer inicio"
       echo "═══════════════════════════════════════"
       /opt/yeyo-os/.venv/bin/python -m src.wizard.installer
       touch "$FIRST_BOOT_FLAG"
   fi
   EOF
   chmod +x "${ROOTFS}/opt/yeyo-os/first-boot.sh"

   # --- Paso 6: User data (opcional) ---
   if [ "$INCLUDE_USERDATA" = true ]; then
       echo "[6.5/8] Incluyendo datos de usuario..."
       if [ -d ~/yeyo-os/data ]; then
           cp -r ~/yeyo-os/data "${ROOTFS}/opt/yeyo-os/"
       fi
   fi

   # --- Paso 7: Crear squashfs ---
   echo "[7/8] Creando filesystem squashfs..."
   mkdir -p "${ISO_DIR}/live"
   mksquashfs "${ROOTFS}" "${ISO_DIR}/live/filesystem.squashfs" \
       -comp xz -b 1M -Xdict-size 100%

   # Copiar kernel e initrd
   cp "${ROOTFS}"/boot/vmlinuz-* "${ISO_DIR}/live/vmlinuz"
   cp "${ROOTFS}"/boot/initrd.img-* "${ISO_DIR}/live/initrd.img"

   # --- Paso 8: Crear ISO con GRUB (UEFI + BIOS) ---
   echo "[8/8] Generando ISO con GRUB..."

   # GRUB config
   mkdir -p "${ISO_DIR}/boot/grub"
   cat > "${ISO_DIR}/boot/grub/grub.cfg" <<EOF
   set timeout=5
   set default=0

   menuentry "YeyoOS ${YEYO_VERSION}" {
       linux /live/vmlinuz boot=live quiet splash
       initrd /live/initrd.img
   }

   menuentry "YeyoOS ${YEYO_VERSION} (Recovery)" {
       linux /live/vmlinuz boot=live single
       initrd /live/initrd.img
   }

   menuentry "Memory Test" {
       linux /live/vmlinuz memtest
   }
   EOF

   # Generar ISO
   grub-mkrescue -o "${OUTPUT_DIR}/${ISO_NAME}" "${ISO_DIR}" \
       --product-name="YeyoOS" \
       --product-version="${YEYO_VERSION}" \
       2>/dev/null

   # --- Resultado ---
   ISO_SIZE=$(du -h "${OUTPUT_DIR}/${ISO_NAME}" | cut -f1)
   ISO_SHA256=$(sha256sum "${OUTPUT_DIR}/${ISO_NAME}" | cut -d' ' -f1)

   echo ""
   echo "═══════════════════════════════════════"
   echo " ✅ ISO generada exitosamente"
   echo "═══════════════════════════════════════"
   echo " Archivo: ${OUTPUT_DIR}/${ISO_NAME}"
   echo " Tamaño:  ${ISO_SIZE}"
   echo " SHA256:  ${ISO_SHA256}"
   echo " Boot:    UEFI + Legacy BIOS"
   echo "═══════════════════════════════════════"

   # Guardar metadata
   cat > "${OUTPUT_DIR}/${ISO_NAME}.meta.json" <<EOF
   {
     "version": "${YEYO_VERSION}",
     "filename": "${ISO_NAME}",
     "size": "${ISO_SIZE}",
     "sha256": "${ISO_SHA256}",
     "built_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
     "ubuntu_release": "${UBUNTU_RELEASE}",
     "include_userdata": ${INCLUDE_USERDATA}
   }
   EOF

   # Limpiar
   echo "Limpiando archivos temporales..."
   rm -rf "${BUILD_DIR}"
   echo "¡Listo! ISO disponible en ${OUTPUT_DIR}/${ISO_NAME}"

3. Hacer ejecutable:
   chmod +x scripts/iso/build_iso.sh

VERIFICAR:
- [ ] Script scripts/iso/build_iso.sh existe y es ejecutable
- [ ] Verifica dependencias (debootstrap, mksquashfs, xorriso, grub-mkrescue)
- [ ] Verifica root (sudo)
- [ ] 8 pasos: limpiar, bootstrap, configurar, paquetes YeyoOS, systemd, wizard, squashfs, ISO
- [ ] Servicios systemd: ollama, yeyo-os, yeyo-guardian, postgresql, redis
- [ ] GRUB config con boot normal, recovery, memtest
- [ ] Output: ISO + metadata JSON con SHA256
- [ ] Soporte UEFI + Legacy BIOS
- [ ] Flag --include-userdata para datos opcionales
- [ ] Limpia archivos temporales al final

SI FALLA:
- Dependencias: apt install debootstrap squashfs-tools xorriso grub-pc-bin grub-efi-amd64-bin mtools
- Sin root: usar sudo

NO HACER:
- No ejecutar build_iso.sh en CI sin espacio en disco suficiente (>10GB)
- No incluir userdata por defecto
- No incluir credenciales en la ISO

GATE: Script genera ISO bootable con todos los componentes de YeyoOS, GRUB UEFI+BIOS, metadata JSON.
```
