## ═══════════════════════════════════════
## MICRO-FASE 7.24 — YeyoNet: ISO Booteable
## Tipo: CLI | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.24-1 [CLI] — ISO booteable de YeyoOS: build-iso.sh con live-build, test en QEMU y documentación de instalación

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.24 de Capa 7 (Evolución): crear una ISO booteable de YeyoOS basada en Debian 12. La ISO debe incluir todo lo necesario para instalar YeyoOS en una PC nueva sin conexión a internet, arrancar automáticamente al boot y completar la instalación en < 30 minutos.

CONTEXTO:
- Micro-fase 7.23 completada: install-satellite.sh y install-central.sh funcionando
- Stack: live-build (Debian), debootstrap, squashfs-tools, xorriso, GRUB2
- Base: Debian 12 (bookworm) minimal — sin escritorio gráfico preinstalado
- Auto-instala: Python 3.11, Docker, Redis, Ollama, Node.js 20, Tailscale
- Auto-configura: YeyoOS al boot, systemd services, CUDA drivers si hay GPU NVIDIA
- Tamaño objetivo: < 4GB (sin modelos Ollama — se descargan en primer boot)
- Boot: GRUB con tema oscuro YeyoOS (fondo azul oscuro, grid, texto blanco)
- UEFI + Legacy BIOS soportados
- test-iso.sh prueba la ISO en QEMU automáticamente

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo scripts/build-iso.sh:

   Ruta: ~/yeyo-os/scripts/build-iso.sh
   Contenido:

   #!/usr/bin/env bash
   # =============================================================================
   # YeyoOS — Build de ISO Booteable
   # Micro-fase 7.24 — Capa 7: Evolución
   #
   # Genera una ISO booteable de YeyoOS basada en Debian 12.
   # Tamaño objetivo: < 4GB. UEFI + Legacy BIOS. GRUB con tema YeyoOS.
   #
   # Dependencias: live-build debootstrap squashfs-tools xorriso syslinux
   # Instalación: sudo apt-get install live-build debootstrap squashfs-tools xorriso syslinux
   #
   # Uso: sudo bash scripts/build-iso.sh [--output=/ruta/yeyo-os.iso] [--version=1.0.0]
   # =============================================================================

   set -euo pipefail
   IFS=$'\n\t'

   # Solo puede correr en Debian/Ubuntu con live-build
   if [[ ! -f /etc/debian_version ]]; then
     echo "❌ build-iso.sh solo soportado en Debian/Ubuntu (requiere live-build)"
     exit 1
   fi

   if [[ $EUID -ne 0 ]]; then
     echo "❌ build-iso.sh requiere root: sudo bash scripts/build-iso.sh"
     exit 1
   fi

   # ── Variables ─────────────────────────────────────────────────────────────────

   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   YEYO_DIR="$(dirname "$SCRIPT_DIR")"
   BUILD_DIR="/tmp/yeyo-iso-build"
   OUTPUT_ISO="${OUTPUT_ISO:-${YEYO_DIR}/dist/yeyo-os.iso}"
   YEYO_VERSION="${YEYO_VERSION:-1.0.0}"
   DEBIAN_CODENAME="bookworm"
   ARCH="amd64"
   LOG_FILE="/tmp/yeyo-build-iso-$(date +%Y%m%d-%H%M%S).log"

   # Parse args
   for arg in "$@"; do
     case "$arg" in
       --output=*) OUTPUT_ISO="${arg#--output=}" ;;
       --version=*) YEYO_VERSION="${arg#--version=}" ;;
     esac
   done

   # ── Colores ───────────────────────────────────────────────────────────────────

   GREEN='\033[0;32m'; BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
   info()    { echo -e "${CYAN}ℹ  ${NC}$*"; }
   success() { echo -e "${GREEN}✅ ${NC}$*"; }
   step()    { echo -e "\n${BOLD}${BLUE}▶ $*${NC}"; }

   # ── Funciones ─────────────────────────────────────────────────────────────────

   check_deps() {
     step "Verificando dependencias de build"

     local missing=()
     for cmd in lb debootstrap mksquashfs xorriso; do
       if ! command -v "$cmd" &>/dev/null; then
         missing+=("$cmd")
       fi
     done

     if [[ ${#missing[@]} -gt 0 ]]; then
       echo "Instalando dependencias faltantes: ${missing[*]}"
       apt-get install -y -qq live-build debootstrap squashfs-tools xorriso syslinux syslinux-common \
         2>&1 | tee -a "$LOG_FILE"
     fi

     success "Dependencias de build verificadas"
   }

   setup_build_dir() {
     step "Configurando directorio de build"

     rm -rf "$BUILD_DIR"
     mkdir -p "$BUILD_DIR"
     cd "$BUILD_DIR"

     # Inicializar live-build
     lb config \
       --distribution "$DEBIAN_CODENAME" \
       --architectures "$ARCH" \
       --binary-images iso-hybrid \
       --debian-installer live \
       --bootloaders "grub-efi,syslinux" \
       --uefi-secure-boot disable \
       --memtest none \
       --iso-application "YeyoOS" \
       --iso-publisher "YeyoOS Project" \
       --iso-volume "YeyoOS-${YEYO_VERSION}" \
       --compression xz \
       --debootstrap-options "--variant=minbase" \
       2>&1 | tee -a "$LOG_FILE"

     success "live-build configurado en $BUILD_DIR"
   }

   configure_packages() {
     step "Configurando lista de paquetes"

     # Paquetes del sistema base
     cat > "${BUILD_DIR}/config/package-lists/yeyo-base.list.chroot" << 'PKGLIST'
   # YeyoOS — Paquetes base del sistema
   # Sistema
   systemd
   sudo
   curl
   wget
   git
   ca-certificates
   gnupg
   lsb-release
   software-properties-common
   apt-transport-https

   # Python 3.11
   python3.11
   python3.11-venv
   python3.11-dev
   python3-pip

   # Redis
   redis-server

   # Audio/Video
   portaudio19-dev
   ffmpeg
   alsa-utils
   pulseaudio

   # Herramientas
   htop
   vim
   less
   tmux
   net-tools
   iproute2
   openssh-client

   # Node.js (se instala manualmente en hooks)
   # Docker (se instala manualmente en hooks)
   # Ollama (se instala manualmente en hooks)
   # Tailscale (se instala manualmente en hooks)
   PKGLIST

     # GRUB themes
     cat > "${BUILD_DIR}/config/package-lists/yeyo-boot.list.chroot" << 'BOOTLIST'
   grub2-common
   grub-efi-amd64
   grub-pc-bin
   BOOTLIST

     success "Lista de paquetes configurada"
   }

   create_hooks() {
     step "Creando hooks de instalación"

     mkdir -p "${BUILD_DIR}/config/hooks/live"
     mkdir -p "${BUILD_DIR}/config/hooks/normal"

     # Hook: instalar Node.js 20
     cat > "${BUILD_DIR}/config/hooks/live/0100-install-nodejs.hook.chroot" << 'HOOK'
   #!/bin/bash
   set -euo pipefail
   echo "📦 Instalando Node.js 20..."
   curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
   apt-get install -y nodejs
   echo "✅ Node.js $(node --version) instalado"
   HOOK

     # Hook: instalar Docker
     cat > "${BUILD_DIR}/config/hooks/live/0200-install-docker.hook.chroot" << 'HOOK'
   #!/bin/bash
   set -euo pipefail
   echo "📦 Instalando Docker..."
   curl -fsSL https://download.docker.com/linux/debian/gpg \
     | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
   echo "deb [arch=amd64 signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
     https://download.docker.com/linux/debian bookworm stable" \
     > /etc/apt/sources.list.d/docker.list
   apt-get update -qq
   apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
   systemctl enable docker
   echo "✅ Docker instalado"
   HOOK

     # Hook: instalar Tailscale
     cat > "${BUILD_DIR}/config/hooks/live/0300-install-tailscale.hook.chroot" << 'HOOK'
   #!/bin/bash
   set -euo pipefail
   echo "📦 Instalando Tailscale..."
   curl -fsSL https://tailscale.com/install.sh | sh
   systemctl enable tailscaled
   echo "✅ Tailscale instalado"
   HOOK

     # Hook: instalar Ollama
     cat > "${BUILD_DIR}/config/hooks/live/0400-install-ollama.hook.chroot" << 'HOOK'
   #!/bin/bash
   set -euo pipefail
   echo "📦 Instalando Ollama..."
   curl -fsSL https://ollama.ai/install.sh | sh
   systemctl enable ollama
   echo "✅ Ollama instalado (modelos se descargan en primer boot)"
   HOOK

     # Hook: clonar YeyoOS y configurar venv
     cat > "${BUILD_DIR}/config/hooks/live/0500-setup-yeyo.hook.chroot" << 'HOOK'
   #!/bin/bash
   set -euo pipefail
   echo "🧠 Configurando YeyoOS..."

   YEYO_DIR="/opt/yeyo-os"
   VENV_DIR="${YEYO_DIR}/.venv"

   # Clonar YeyoOS (en producción usar el repo oficial)
   if [[ ! -d "${YEYO_DIR}/.git" ]]; then
     git clone --depth=1 "${YEYO_REPO:-https://github.com/yeyoa/yeyo-os.git}" "$YEYO_DIR"
   fi

   # Crear venv
   python3.11 -m venv "$VENV_DIR"
   "${VENV_DIR}/bin/pip" install --quiet --upgrade pip
   "${VENV_DIR}/bin/pip" install --quiet -r "${YEYO_DIR}/requirements.txt" || true

   # Build del frontend
   cd "${YEYO_DIR}/frontend"
   npm install --silent || true
   npm run build --silent || true

   echo "✅ YeyoOS configurado en $YEYO_DIR"
   HOOK

     # Hook: instalar servicios systemd
     cat > "${BUILD_DIR}/config/hooks/live/0600-systemd-services.hook.chroot" << 'HOOK'
   #!/bin/bash
   set -euo pipefail
   echo "⚙️  Configurando servicios systemd..."

   YEYO_DIR="/opt/yeyo-os"
   VENV_DIR="${YEYO_DIR}/.venv"

   cat > /etc/systemd/system/yeyo-backend.service << SVC
   [Unit]
   Description=YeyoOS Backend (FastAPI)
   After=network.target redis.service

   [Service]
   WorkingDirectory=${YEYO_DIR}
   ExecStart=${VENV_DIR}/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000
   Restart=always
   RestartSec=5
   Environment=PYTHONPATH=${YEYO_DIR}
   Environment=REDIS_URL=redis://localhost:6379/0

   [Install]
   WantedBy=multi-user.target
   SVC

   cat > /etc/systemd/system/yeyo-worker.service << SVC
   [Unit]
   Description=YeyoOS Celery Worker
   After=redis.service yeyo-backend.service

   [Service]
   WorkingDirectory=${YEYO_DIR}
   ExecStart=${VENV_DIR}/bin/celery -A src.cluster.worker.celery_app worker \
     --loglevel=info --concurrency=2 --queues=gpu_tasks,cpu_tasks,training_tasks
   Restart=always
   RestartSec=10
   Environment=PYTHONPATH=${YEYO_DIR}
   Environment=REDIS_URL=redis://localhost:6379/0

   [Install]
   WantedBy=multi-user.target
   SVC

   systemctl enable redis-server yeyo-backend yeyo-worker
   echo "✅ Servicios systemd configurados"
   HOOK

     # Hook: detectar GPU NVIDIA y configurar CUDA
     cat > "${BUILD_DIR}/config/hooks/live/0700-nvidia-cuda.hook.chroot" << 'HOOK'
   #!/bin/bash
   # Detectar si hay GPU NVIDIA y pre-instalar drivers
   if lspci 2>/dev/null | grep -qi nvidia; then
     echo "🎮 GPU NVIDIA detectada — instalando drivers..."
     apt-get install -y -qq nvidia-detect
     DRIVER=$(nvidia-detect | grep -oP 'nvidia-driver-\d+' | head -1)
     if [[ -n "$DRIVER" ]]; then
       apt-get install -y "$DRIVER" || echo "⚠️  Driver $DRIVER no pudo instalarse en build"
     fi
   else
     echo "ℹ️  Sin GPU NVIDIA detectada — omitiendo CUDA"
   fi
   HOOK

     chmod +x "${BUILD_DIR}/config/hooks/live/"*.hook.chroot
     success "Hooks de instalación creados"
   }

   create_grub_theme() {
     step "Creando tema GRUB YeyoOS"

     local theme_dir="${BUILD_DIR}/config/bootloaders/grub-pc/theme"
     mkdir -p "$theme_dir"

     # Configuración principal del tema
     cat > "${theme_dir}/theme.txt" << 'THEME'
   # YeyoOS GRUB Theme
   # Fondo azul oscuro, grid, texto blanco

   title-text: "YeyoOS"
   title-font: "DejaVu Sans Bold 24"
   title-color: "#ffffff"

   desktop-color: "#0a0a1a"
   desktop-image: "background.png"

   + label {
     text = "YeyoOS — IA Personal"
     font = "DejaVu Sans Bold 16"
     color = "#6366f1"
     align = center
     preferred-size = 400, 30
   }

   + boot_menu {
     left = 10%
     top = 25%
     width = 80%
     height = 50%
     item-font = "DejaVu Sans 14"
     item-color = "#a0aec0"
     selected-item-font = "DejaVu Sans Bold 14"
     selected-item-color = "#ffffff"
     selected-item-background = "#1e1b4b"
     item-padding = 10
     item-spacing = 5
     scrollbar = false
   }

   + progress_bar {
     id = "__timeout__"
     left = 10%
     top = 80%
     width = 80%
     height = 4
     show-text = false
     fg-color = "#6366f1"
     bg-color = "#1e1b4b"
   }
   THEME

     # Crear fondo simple (PNG placeholder — en producción usar imagen real)
     # Generar fondo azul oscuro con Python si está disponible
     python3 - << 'PYIMG' || true
   try:
       from PIL import Image, ImageDraw
       img = Image.new('RGB', (1920, 1080), color=(10, 10, 26))
       draw = ImageDraw.Draw(img)
       # Dibujar grid sutil
       for x in range(0, 1920, 80):
           draw.line([(x, 0), (x, 1080)], fill=(20, 20, 50), width=1)
       for y in range(0, 1080, 80):
           draw.line([(0, y), (1920, y)], fill=(20, 20, 50), width=1)
       img.save('/tmp/yeyo-background.png')
       print("Fondo generado")
   except ImportError:
       pass
   PYIMG

     if [[ -f /tmp/yeyo-background.png ]]; then
       cp /tmp/yeyo-background.png "${theme_dir}/background.png"
     fi

     # Configuración de GRUB
     mkdir -p "${BUILD_DIR}/config/includes.chroot/etc/default"
     cat > "${BUILD_DIR}/config/includes.chroot/etc/default/grub" << 'GRUBCFG'
   GRUB_DEFAULT=0
   GRUB_TIMEOUT=5
   GRUB_TIMEOUT_STYLE=menu
   GRUB_DISTRIBUTOR="YeyoOS"
   GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
   GRUB_CMDLINE_LINUX=""
   GRUB_BACKGROUND="/boot/grub/theme/background.png"
   GRUB_THEME="/boot/grub/theme/theme.txt"
   GRUB_GFXMODE=1920x1080,1280x720,auto
   GRUBCFG

     success "Tema GRUB creado"
   }

   configure_auto_start() {
     step "Configurando auto-inicio de YeyoOS al boot"

     mkdir -p "${BUILD_DIR}/config/includes.chroot/etc/systemd/system"

     # Servicio que abre el onboarding en el primer boot
     cat > "${BUILD_DIR}/config/includes.chroot/etc/systemd/system/yeyo-firstboot.service" << 'SVC'
   [Unit]
   Description=YeyoOS First Boot Setup
   After=network-online.target ollama.service
   ConditionPathExists=!/etc/yeyo-configured

   [Service]
   Type=oneshot
   ExecStart=/opt/yeyo-os/scripts/install-satellite.sh --mode=completo --yes
   ExecStartPost=/bin/bash -c "touch /etc/yeyo-configured"
   RemainAfterExit=yes
   StandardOutput=journal
   StandardError=journal

   [Install]
   WantedBy=multi-user.target
   SVC

     # Servicio que abre el navegador en el desktop (si hay)
     cat > "${BUILD_DIR}/config/includes.chroot/etc/systemd/system/yeyo-browser.service" << 'SVC'
   [Unit]
   Description=YeyoOS Frontend en navegador
   After=yeyo-backend.service
   Wants=yeyo-backend.service

   [Service]
   Type=oneshot
   ExecStart=/bin/bash -c "sleep 5 && xdg-open http://localhost:3000/onboarding"
   Environment=DISPLAY=:0

   [Install]
   WantedBy=graphical.target
   SVC

     success "Auto-inicio configurado"
   }

   build_iso() {
     step "Construyendo ISO (esto puede tardar 30-60 minutos)"

     cd "$BUILD_DIR"

     info "Iniciando lb build..."
     lb build 2>&1 | tee -a "$LOG_FILE"

     # Encontrar el ISO generado
     local built_iso
     built_iso=$(find "$BUILD_DIR" -name "*.iso" -newer "$BUILD_DIR/config" 2>/dev/null | head -1)

     if [[ -z "$built_iso" ]]; then
       echo "❌ ISO no generado — revisar log: $LOG_FILE"
       exit 1
     fi

     # Copiar al destino final
     mkdir -p "$(dirname "$OUTPUT_ISO")"
     cp "$built_iso" "$OUTPUT_ISO"

     local iso_size_mb
     iso_size_mb=$(du -m "$OUTPUT_ISO" | cut -f1)
     success "ISO generado: $OUTPUT_ISO (${iso_size_mb}MB)"

     if [[ "$iso_size_mb" -gt 4096 ]]; then
       echo "⚠️  ISO supera 4GB (${iso_size_mb}MB) — considerar eliminar modelos Ollama del build"
     fi
   }

   generate_checksums() {
     step "Generando checksums"

     local iso_dir
     iso_dir="$(dirname "$OUTPUT_ISO")"

     sha256sum "$OUTPUT_ISO" > "${iso_dir}/yeyo-os.iso.sha256"
     md5sum "$OUTPUT_ISO" > "${iso_dir}/yeyo-os.iso.md5"

     success "Checksums generados en $iso_dir"
   }

   # ── Main ──────────────────────────────────────────────────────────────────────

   main() {
     echo -e "\n${BOLD}${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
     echo -e "${BOLD}${BLUE}║         YeyoOS — Build de ISO Booteable v${YEYO_VERSION}         ║${NC}"
     echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"
     echo -e "  Output: ${CYAN}$OUTPUT_ISO${NC}"
     echo -e "  Log:    ${CYAN}$LOG_FILE${NC}\n"

     check_deps
     setup_build_dir
     configure_packages
     create_hooks
     create_grub_theme
     configure_auto_start
     build_iso
     generate_checksums

     echo ""
     echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
     echo -e "${BOLD}${GREEN}║              🎉 ISO Generado Exitosamente              ║${NC}"
     echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
     echo ""
     echo -e "  ISO: ${CYAN}$OUTPUT_ISO${NC}"
     echo ""
     echo -e "  ${BOLD}Crear USB booteable:${NC}"
     echo -e "  ${CYAN}sudo dd if=$OUTPUT_ISO of=/dev/sdX bs=4M status=progress && sync${NC}"
     echo -e "  ${CYAN}# O usar: sudo cp $OUTPUT_ISO /dev/sdX && sync${NC}"
     echo ""
     echo -e "  ${BOLD}Probar en QEMU:${NC}"
     echo -e "  ${CYAN}bash scripts/test-iso.sh --iso=$OUTPUT_ISO${NC}"
   }

   main "$@"

2. Crear archivo scripts/test-iso.sh:

   Ruta: ~/yeyo-os/scripts/test-iso.sh
   Contenido:

   #!/usr/bin/env bash
   # =============================================================================
   # YeyoOS — Test de ISO en QEMU
   # Micro-fase 7.24 — Capa 7: Evolución
   #
   # Prueba la ISO generada en QEMU automáticamente.
   # Verifica que bootea, que YeyoOS inicia y que los servicios responden.
   #
   # Uso: bash scripts/test-iso.sh --iso=/ruta/yeyo-os.iso [--headless] [--timeout=300]
   # =============================================================================

   set -euo pipefail
   IFS=$'\n\t'

   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   ISO_PATH=""
   HEADLESS=false
   TIMEOUT=300
   QEMU_RAM="4096"
   QEMU_CPUS="2"
   QEMU_PORT="10022"   # SSH forwarding port
   HTTP_PORT="10080"   # HTTP forwarding para verificar el backend
   QEMU_PID_FILE="/tmp/yeyo-qemu.pid"
   PASS_COUNT=0
   FAIL_COUNT=0

   GREEN='\033[0;32m'; RED='\033[0;31m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'
   info()    { echo -e "${CYAN}ℹ  ${NC}$*"; }
   success() { echo -e "${GREEN}✅ ${NC}$*"; ((PASS_COUNT++)); }
   failure() { echo -e "${RED}❌ ${NC}$*"; ((FAIL_COUNT++)); }
   step()    { echo -e "\n${BOLD}▶ $*${NC}"; }

   for arg in "$@"; do
     case "$arg" in
       --iso=*) ISO_PATH="${arg#--iso=}" ;;
       --headless) HEADLESS=true ;;
       --timeout=*) TIMEOUT="${arg#--timeout=}" ;;
       --ram=*) QEMU_RAM="${arg#--ram=}" ;;
     esac
   done

   check_iso_exists() {
     step "Verificando ISO"
     if [[ -z "$ISO_PATH" ]]; then
       # Buscar ISO en dist/
       ISO_PATH=$(find "$(dirname "$SCRIPT_DIR")/dist" -name "*.iso" 2>/dev/null | head -1)
     fi
     if [[ ! -f "$ISO_PATH" ]]; then
       failure "ISO no encontrada: ${ISO_PATH:-no especificada}"
       echo "Genera la ISO primero: sudo bash scripts/build-iso.sh"
       exit 1
     fi
     success "ISO encontrada: $ISO_PATH ($(du -mh "$ISO_PATH" | cut -f1))"
   }

   check_qemu() {
     step "Verificando QEMU"
     if ! command -v qemu-system-x86_64 &>/dev/null; then
       info "Instalando QEMU..."
       sudo apt-get install -y -qq qemu-system-x86 qemu-utils ovmf 2>/dev/null || \
       sudo pacman -S --noconfirm qemu-full 2>/dev/null || true
     fi

     if command -v qemu-system-x86_64 &>/dev/null; then
       success "QEMU disponible: $(qemu-system-x86_64 --version | head -1)"
     else
       failure "QEMU no disponible — instalar manualmente"
       exit 1
     fi
   }

   check_iso_size() {
     step "Verificando tamaño de ISO"
     local size_mb
     size_mb=$(du -m "$ISO_PATH" | cut -f1)
     if [[ "$size_mb" -le 4096 ]]; then
       success "Tamaño OK: ${size_mb}MB (≤ 4GB)"
     else
       failure "ISO demasiado grande: ${size_mb}MB (objetivo: ≤ 4096MB)"
     fi
   }

   check_iso_checksum() {
     step "Verificando checksum"
     local sha_file="${ISO_PATH}.sha256"
     if [[ -f "$sha_file" ]]; then
       if sha256sum -c "$sha_file" --quiet 2>/dev/null; then
         success "Checksum SHA256 válido"
       else
         failure "Checksum SHA256 inválido — ISO corrupta"
       fi
     else
       info "Sin archivo .sha256 para verificar — omitiendo"
     fi
   }

   start_qemu() {
     step "Iniciando QEMU con la ISO"

     local qemu_args=(
       qemu-system-x86_64
       -m "${QEMU_RAM}M"
       -smp "${QEMU_CPUS}"
       -cdrom "$ISO_PATH"
       -boot d
       -netdev "user,id=net0,hostfwd=tcp::${QEMU_PORT}-:22,hostfwd=tcp::${HTTP_PORT}-:8000"
       -device "e1000,netdev=net0"
       -enable-kvm
       -daemonize
       -pidfile "$QEMU_PID_FILE"
     )

     if [[ "$HEADLESS" == "true" ]]; then
       qemu_args+=(-display none -nographic)
     else
       qemu_args+=(-display sdl)
     fi

     # KVM puede no estar disponible en CI
     if [[ ! -r /dev/kvm ]]; then
       qemu_args=("${qemu_args[@]//-enable-kvm}")
       qemu_args+=(-accel tcg)
       info "KVM no disponible — usando TCG (más lento)"
     fi

     info "Iniciando QEMU (RAM=${QEMU_RAM}MB, CPUs=${QEMU_CPUS})..."
     "${qemu_args[@]}" 2>/dev/null || {
       info "QEMU con KVM falló — intentando sin KVM..."
       qemu-system-x86_64 \
         -m "${QEMU_RAM}M" \
         -smp "${QEMU_CPUS}" \
         -cdrom "$ISO_PATH" \
         -boot d \
         -netdev "user,id=net0,hostfwd=tcp::${HTTP_PORT}-:8000" \
         -device "e1000,netdev=net0" \
         -display none \
         -daemonize \
         -pidfile "$QEMU_PID_FILE"
     }

     success "QEMU iniciado (PID: $(cat "$QEMU_PID_FILE" 2>/dev/null || echo '?'))"
   }

   wait_for_boot() {
     step "Esperando que la VM bootee (timeout: ${TIMEOUT}s)"

     local elapsed=0
     local interval=10

     while [[ $elapsed -lt $TIMEOUT ]]; do
       if curl -s --max-time 5 "http://localhost:${HTTP_PORT}/health" &>/dev/null; then
         success "YeyoOS backend respondió en ${elapsed}s"
         return 0
       fi
       info "Esperando... ${elapsed}s/${TIMEOUT}s"
       sleep "$interval"
       elapsed=$((elapsed + interval))
     done

     failure "Timeout: YeyoOS no respondió en ${TIMEOUT}s"
     return 1
   }

   test_backend_health() {
     step "Verificando health del backend"

     local resp
     resp=$(curl -s --max-time 10 "http://localhost:${HTTP_PORT}/health" 2>/dev/null || echo "")

     if [[ -n "$resp" ]]; then
       success "Backend responde: $resp"
     else
       failure "Backend no responde en http://localhost:${HTTP_PORT}/health"
     fi
   }

   test_cluster_api() {
     step "Verificando Cluster API"

     local resp
     resp=$(curl -s --max-time 10 "http://localhost:${HTTP_PORT}/api/cluster/nodes/status" 2>/dev/null || echo "")

     if echo "$resp" | python3 -c "import sys, json; json.load(sys.stdin)" 2>/dev/null; then
       success "Cluster API responde con JSON válido"
     else
       failure "Cluster API no responde: $resp"
     fi
   }

   stop_qemu() {
     step "Deteniendo QEMU"

     if [[ -f "$QEMU_PID_FILE" ]]; then
       local pid
       pid=$(cat "$QEMU_PID_FILE")
       kill "$pid" 2>/dev/null || true
       rm -f "$QEMU_PID_FILE"
       success "QEMU detenido (PID: $pid)"
     fi
   }

   print_results() {
     echo ""
     echo -e "${BOLD}═══════════════════════════════════════${NC}"
     echo -e "${BOLD}RESULTADOS DEL TEST DE ISO${NC}"
     echo -e "${BOLD}═══════════════════════════════════════${NC}"
     echo -e "  ✅ Pasaron: ${GREEN}${PASS_COUNT}${NC}"
     echo -e "  ❌ Fallaron: ${RED}${FAIL_COUNT}${NC}"
     echo ""

     if [[ $FAIL_COUNT -eq 0 ]]; then
       echo -e "${GREEN}${BOLD}🎉 ISO verificada exitosamente${NC}"
       exit 0
     else
       echo -e "${RED}${BOLD}❌ $FAIL_COUNT test(s) fallaron${NC}"
       exit 1
     fi
   }

   main() {
     echo -e "\n${BOLD}${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
     echo -e "${BOLD}${BLUE}║              YeyoOS — Test de ISO en QEMU              ║${NC}"
     echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════╝${NC}\n"

     trap stop_qemu EXIT

     check_iso_exists
     check_qemu
     check_iso_size
     check_iso_checksum

     # Tests que requieren arrancar la VM
     if [[ "${SKIP_VM:-false}" != "true" ]]; then
       start_qemu
       wait_for_boot && {
         test_backend_health
         test_cluster_api
       } || true
     else
       info "SKIP_VM=true — omitiendo tests de VM"
     fi

     print_results
   }

   main "$@"

3. Crear archivo docs/17-instalacion.md:

   Ruta: ~/yeyo-os/docs/17-instalacion.md
   Contenido:

   # 17 — Instalación de YeyoOS

   ## Requisitos mínimos

   | Componente | Mínimo | Recomendado |
   |:---|:---:|:---:|
   | **CPU** | Dual-core 2GHz (x86_64) | Intel i5 / AMD Ryzen 5 |
   | **RAM** | 8 GB | 16 GB |
   | **Almacenamiento** | 50 GB SSD | 100 GB SSD NVMe |
   | **GPU (opcional)** | Sin GPU (Modo Ligero) | NVIDIA GTX 1060 6GB+ |
   | **Red** | Ethernet / WiFi 802.11n | Ethernet Gigabit |
   | **OS host** | Ubuntu 22.04 / Debian 12 / Arch | Ubuntu 22.04 LTS |

   ## Método 1: USB Booteable (recomendado para PC nueva)

   ### 1. Descargar la ISO

   ```bash
   # Descargar la última versión
   wget https://github.com/yeyoa/yeyo-os/releases/latest/download/yeyo-os.iso
   wget https://github.com/yeyoa/yeyo-os/releases/latest/download/yeyo-os.iso.sha256

   # Verificar integridad
   sha256sum -c yeyo-os.iso.sha256
   ```

   ### 2. Crear USB booteable

   ```bash
   # Identificar el USB (reemplazar /dev/sdX con tu dispositivo)
   lsblk

   # Escribir la ISO (⚠️ BORRA TODOS LOS DATOS del USB)
   sudo dd if=yeyo-os.iso of=/dev/sdX bs=4M status=progress && sync
   ```

   Alternativas gráficas: **Balena Etcher**, **Rufus** (Windows), **GNOME Disks**.

   ### 3. Arrancar desde el USB

   1. Reiniciar la PC con el USB conectado
   2. Entrar al BIOS/UEFI (F2, F12, Del — varía según fabricante)
   3. Cambiar el orden de boot: USB primero
   4. Guardar y reiniciar
   5. Seleccionar **"Instalar YeyoOS"** en el menú GRUB

   ### 4. Proceso de instalación automática

   La instalación es completamente automática:

   ```
   ┌────────────────────────────────────────────────┐
   │  YeyoOS — Instalación automática               │
   │                                                │
   │  [████████████░░░░░░░] 60% — Configurando...   │
   │                                                │
   │  • ✅ Sistema base                             │
   │  • ✅ Python 3.11 + dependencias               │
   │  • ✅ Docker                                   │
   │  • ✅ Redis                                    │
   │  • ✅ Tailscale                                │
   │  • 🔄 Ollama (descargando modelos...)          │
   │  • ⏳ YeyoOS servicios                         │
   └────────────────────────────────────────────────┘
   ```

   Tiempo estimado: **15-25 minutos** según velocidad de internet.

   Al terminar, YeyoOS abre automáticamente en `http://localhost:3000`.

   ## Método 2: Script en sistema existente

   Si ya tienes Ubuntu/Debian/Arch instalado:

   ```bash
   # Instalar como satélite (modo completo)
   curl -fsSL https://raw.githubusercontent.com/yeyoa/yeyo-os/main/scripts/install-satellite.sh | bash

   # Instalar como Central
   curl -fsSL https://raw.githubusercontent.com/yeyoa/yeyo-os/main/scripts/install-central.sh | bash
   ```

   O clonar el repositorio primero:

   ```bash
   git clone https://github.com/yeyoa/yeyo-os.git ~/yeyo-os
   bash ~/yeyo-os/scripts/install-satellite.sh --mode=completo
   ```

   ### Modos de instalación

   | Modo | Modelos | VRAM | Uso |
   |:---|:---:|:---:|:---|
   | `completo` | qwen2.5:3b + 0.5b | 4GB+ recomendada | PC principal |
   | `ligero` | qwen2.5:0.5b | Sin GPU | Laptop de viaje |
   | `minimo` | Ninguno | Sin GPU | PC muy antigua |

   ## Conectar a un Central (YeyoNet)

   Tras la instalación, conectar el satélite a un Central:

   1. El **dueño del Central** genera un código en `http://central:3000/yeyonet → + Invitar`
   2. El código tiene formato `YEYO-XXXX-XXXX-XXXX`
   3. En el **satélite**, abrir `http://localhost:3000/onboarding`
   4. Ingresar el código de invitación
   5. La conexión se establece automáticamente via Tailscale

   ## Gestión de servicios

   ```bash
   # Ver estado de todos los servicios YeyoOS
   systemctl --user status yeyo-backend yeyo-worker yeyo-frontend

   # Iniciar/detener
   systemctl --user start yeyo-backend yeyo-worker
   systemctl --user stop yeyo-backend

   # Ver logs en tiempo real
   journalctl --user -u yeyo-backend -f

   # Reiniciar tras actualización
   systemctl --user restart yeyo-backend yeyo-worker
   ```

   ## Actualizar YeyoOS

   ```bash
   cd ~/yeyo-os
   git pull
   .venv/bin/pip install -r requirements.txt
   cd frontend && npm install && npm run build
   systemctl --user restart yeyo-backend yeyo-worker yeyo-frontend
   ```

   ## Solución de problemas

   ### Backend no inicia

   ```bash
   journalctl --user -u yeyo-backend -n 50
   # Verificar que Redis está corriendo
   redis-cli ping  # debe responder PONG
   ```

   ### Modelos Ollama no disponibles

   ```bash
   ollama list  # ver modelos instalados
   ollama pull qwen2.5:3b  # descargar modelo
   ```

   ### Tailscale no conecta

   ```bash
   sudo tailscale up  # autenticar con la cuenta Tailscale
   tailscale status   # ver estado de la red
   ```

   ### ISO no bootea

   - Verificar que el USB fue creado con `dd` (no solo copiado)
   - En BIOS: deshabilitar Secure Boot si está habilitado
   - Probar en modo Legacy/MBR si UEFI falla

   ## Build de la ISO (para desarrolladores)

   ```bash
   # En Ubuntu/Debian con live-build instalado
   sudo apt-get install live-build debootstrap squashfs-tools xorriso syslinux
   sudo bash scripts/build-iso.sh --output=dist/yeyo-os.iso

   # Probar en QEMU
   bash scripts/test-iso.sh --iso=dist/yeyo-os.iso --headless --timeout=300
   ```

VERIFICAR:
- [ ] scripts/build-iso.sh — 8 pasos, configura live-build, hooks para Docker/Node/Tailscale/Ollama, tema GRUB, auto-inicio
- [ ] scripts/test-iso.sh — verifica ISO existe, tamaño ≤4GB, checksum, bootea en QEMU
- [ ] docs/17-instalacion.md — documentación completa con requisitos, métodos y troubleshooting
- [ ] bash -n scripts/build-iso.sh — sintaxis válida
- [ ] bash -n scripts/test-iso.sh — sintaxis válida

SI FALLA:
- live-build no disponible: solo en Debian/Ubuntu — documentado como requisito
- QEMU no disponible en CI: usar SKIP_VM=true para tests sin VM
- ISO demasiado grande: reducir paquetes en package-lists o excluir drivers NVIDIA del build
- Hooks fallan en chroot: verificar que los comandos (curl, git) están disponibles en el chroot
- GRUB theme no se aplica: verificar rutas en /etc/default/grub coinciden con archivos copiados

NO HACER:
- No incluir modelos Ollama en la ISO (>4GB) — se descargan en primer boot
- No hardcodear contraseñas en hooks
- No requerir conexión a internet para el test de sintaxis (bash -n)
- No incluir datos de usuario ni Flash Memory en la ISO
- No implementar un installer gráfico complejo (usar el script install-satellite.sh existente)

GATE: bash -n scripts/build-iso.sh y bash -n scripts/test-iso.sh pasan sin errores de sintaxis. scripts/build-iso.sh con live-build genera ISO en dist/yeyo-os.iso < 4GB. scripts/test-iso.sh verifica checksum y tamaño. SKIP_VM=true test pasa (≥4 checks). docs/17-instalacion.md documenta USB booteable, script en sistema existente, gestión de servicios y troubleshooting.
```
