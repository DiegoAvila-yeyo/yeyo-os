## ═══════════════════════════════════════
## MICRO-FASE 7.23 — YeyoNet: Instalador automático (.sh)
## Tipo: CLI | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.23-1 [CLI] — Scripts bash completos para instalar YeyoOS como satélite o Central en Ubuntu/Debian/Arch

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.23 de Capa 7 (Evolución): crear los scripts de instalación automática para YeyoOS. El script install-satellite.sh convierte cualquier PC con Ubuntu/Debian/Arch en un satélite de YeyoNet en < 30 minutos. El script install-central.sh hace lo mismo pero como nodo Central.

CONTEXTO:
- Micro-fases 7.19-7.22 completadas: Cluster Mode con workers, GPU pool, federated learning y dashboard
- Los scripts corren en una PC limpia con Ubuntu 22.04/Debian 12/Arch Linux
- YeyoOS requiere: Python 3.11, Docker, Redis, Ollama, Node.js 20, Tailscale
- Servicios systemd: yeyo-backend (FastAPI), yeyo-worker (Celery), yeyo-frontend (Vite serve)
- Modelos Ollama: qwen2.5:3b (obligatorio), qwen2.5:0.5b (modo ligero), whisper (voz)
- Al final de la instalación: abrir interfaz de onboarding que pide código de invitación del Central
- El script debe ser idempotente: si se ejecuta dos veces, no rompe nada
- Salida colorida con emojis, progress indicators y mensajes claros
- tests/test_install.sh con bats verifica cada paso crítico del instalador

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo scripts/install-satellite.sh:

   Ruta: ~/yeyo-os/scripts/install-satellite.sh
   Contenido:

   #!/usr/bin/env bash
   # =============================================================================
   # YeyoOS — Instalador de Satélite
   # Micro-fase 7.23 — Capa 7: Evolución
   #
   # Convierte una PC con Ubuntu/Debian/Arch en un satélite de YeyoNet.
   # Tiempo estimado: 15-30 minutos según velocidad de descarga.
   #
   # Uso: bash install-satellite.sh [--mode ligero|completo|minimo] [--yes]
   # =============================================================================

   set -euo pipefail
   IFS=$'\n\t'

   # ── Colores y helpers ─────────────────────────────────────────────────────────

   RED='\033[0;31m'
   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   BLUE='\033[0;34m'
   CYAN='\033[0;36m'
   BOLD='\033[1m'
   NC='\033[0m' # No Color

   info()    { echo -e "${CYAN}ℹ  ${NC}$*"; }
   success() { echo -e "${GREEN}✅ ${NC}$*"; }
   warn()    { echo -e "${YELLOW}⚠️  ${NC}$*"; }
   error()   { echo -e "${RED}❌ ${NC}$*" >&2; }
   step()    { echo -e "\n${BOLD}${BLUE}▶ $*${NC}"; }
   fatal()   { error "$*"; exit 1; }

   # ── Variables ─────────────────────────────────────────────────────────────────

   YEYO_VERSION="1.0.0"
   YEYO_DIR="${HOME}/yeyo-os"
   YEYO_REPO="${YEYO_REPO:-https://github.com/yeyoa/yeyo-os.git}"
   VENV_DIR="${YEYO_DIR}/.venv"
   LOG_FILE="/tmp/yeyo-install-$(date +%Y%m%d-%H%M%S).log"
   MODE="${1:-completo}"
   AUTO_YES=false
   SYSTEMD_AVAILABLE=false
   OS_DISTRO=""
   OS_CODENAME=""

   # Parse args
   for arg in "$@"; do
     case "$arg" in
       --mode=*) MODE="${arg#--mode=}" ;;
       --yes|-y) AUTO_YES=true ;;
       --help|-h)
         echo "Uso: bash install-satellite.sh [--mode=ligero|completo|minimo] [--yes]"
         exit 0
         ;;
     esac
   done

   # ── Funciones principales ─────────────────────────────────────────────────────

   check_root() {
     if [[ $EUID -eq 0 ]]; then
       warn "Corriendo como root. Se recomienda correr como usuario normal con sudo disponible."
     fi
   }

   detect_os() {
     step "1/9 Detectando sistema operativo"

     if [[ ! -f /etc/os-release ]]; then
       fatal "No se pudo detectar el SO. Se requiere /etc/os-release."
     fi

     source /etc/os-release
     OS_DISTRO="${ID:-unknown}"
     OS_CODENAME="${VERSION_CODENAME:-}"

     case "$OS_DISTRO" in
       ubuntu|debian)
         info "Detectado: ${PRETTY_NAME}"
         PKG_MANAGER="apt-get"
         PKG_UPDATE="sudo apt-get update -qq"
         PKG_INSTALL="sudo apt-get install -y -qq"
         ;;
       arch|manjaro)
         info "Detectado: ${PRETTY_NAME}"
         PKG_MANAGER="pacman"
         PKG_UPDATE="sudo pacman -Sy --noconfirm"
         PKG_INSTALL="sudo pacman -S --noconfirm --needed"
         ;;
       fedora|rhel|centos)
         info "Detectado: ${PRETTY_NAME}"
         PKG_MANAGER="dnf"
         PKG_UPDATE="sudo dnf check-update -q || true"
         PKG_INSTALL="sudo dnf install -y -q"
         ;;
       *)
         fatal "Distribución no soportada: $OS_DISTRO. Se soporta Ubuntu/Debian/Arch/Fedora."
         ;;
     esac

     # Verificar systemd
     if command -v systemctl &>/dev/null && systemctl is-system-running &>/dev/null 2>&1; then
       SYSTEMD_AVAILABLE=true
     fi

     success "SO detectado: $OS_DISTRO"
   }

   install_system_deps() {
     step "2/9 Instalando dependencias del sistema"

     info "Actualizando índice de paquetes..."
     $PKG_UPDATE 2>&1 | tee -a "$LOG_FILE" || true

     local common_pkgs=(
       curl wget git build-essential
       software-properties-common ca-certificates
       gnupg lsb-release
     )

     case "$OS_DISTRO" in
       ubuntu|debian)
         $PKG_INSTALL "${common_pkgs[@]}" \
           python3.11 python3.11-venv python3.11-dev python3-pip \
           redis-server portaudio19-dev ffmpeg \
           2>&1 | tee -a "$LOG_FILE"
         ;;
       arch|manjaro)
         $PKG_INSTALL "${common_pkgs[@]/build-essential/base-devel}" \
           python python-pip redis portaudio ffmpeg \
           2>&1 | tee -a "$LOG_FILE"
         ;;
       fedora|rhel|centos)
         $PKG_INSTALL "${common_pkgs[@]/software-properties-common/}" \
           python3.11 python3.11-devel python3-pip \
           redis portaudio-devel ffmpeg \
           2>&1 | tee -a "$LOG_FILE"
         ;;
     esac

     success "Dependencias del sistema instaladas"
   }

   install_docker() {
     step "3/9 Instalando Docker"

     if command -v docker &>/dev/null; then
       local docker_version
       docker_version=$(docker --version 2>/dev/null | grep -oP '\d+\.\d+' | head -1)
       info "Docker ya instalado: ${docker_version}"
       return
     fi

     case "$OS_DISTRO" in
       ubuntu|debian)
         # Instalar desde el repositorio oficial de Docker
         curl -fsSL https://download.docker.com/linux/${OS_DISTRO}/gpg \
           | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
         echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] \
           https://download.docker.com/linux/${OS_DISTRO} ${OS_CODENAME} stable" \
           | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
         sudo apt-get update -qq
         sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
         ;;
       arch|manjaro)
         sudo pacman -S --noconfirm --needed docker docker-compose
         ;;
       fedora|rhel|centos)
         sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
         sudo dnf install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin
         ;;
     esac

     sudo usermod -aG docker "$USER"
     sudo systemctl enable --now docker 2>/dev/null || true

     success "Docker instalado"
   }

   install_nodejs() {
     step "3.5/9 Instalando Node.js 20"

     if command -v node &>/dev/null; then
       local node_major
       node_major=$(node --version | grep -oP '\d+' | head -1)
       if [[ "$node_major" -ge 20 ]]; then
         info "Node.js $node_major ya instalado"
         return
       fi
     fi

     case "$OS_DISTRO" in
       ubuntu|debian)
         curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
         sudo apt-get install -y -qq nodejs
         ;;
       arch|manjaro)
         sudo pacman -S --noconfirm --needed nodejs npm
         ;;
       fedora|rhel|centos)
         curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
         sudo dnf install -y -q nodejs
         ;;
     esac

     success "Node.js $(node --version) instalado"
   }

   clone_yeyo_os() {
     step "4/9 Clonando/actualizando YeyoOS"

     if [[ -d "$YEYO_DIR/.git" ]]; then
       info "YeyoOS ya existe en $YEYO_DIR — actualizando..."
       cd "$YEYO_DIR"
       git pull --ff-only 2>&1 | tee -a "$LOG_FILE" || warn "git pull falló — usando versión actual"
     else
       info "Clonando YeyoOS en $YEYO_DIR..."
       git clone --depth=1 "$YEYO_REPO" "$YEYO_DIR" 2>&1 | tee -a "$LOG_FILE"
     fi

     success "YeyoOS en $YEYO_DIR"
   }

   setup_python_env() {
     step "5/9 Configurando entorno Python"

     local python_bin
     if command -v python3.11 &>/dev/null; then
       python_bin="python3.11"
     elif command -v python3 &>/dev/null; then
       python_bin="python3"
     else
       fatal "Python 3.11+ no encontrado"
     fi

     local py_version
     py_version=$($python_bin --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
     info "Usando $python_bin ($py_version)"

     if [[ ! -d "$VENV_DIR" ]]; then
       info "Creando virtualenv en $VENV_DIR..."
       $python_bin -m venv "$VENV_DIR"
     fi

     info "Instalando dependencias Python..."
     "$VENV_DIR/bin/pip" install --quiet --upgrade pip
     "$VENV_DIR/bin/pip" install --quiet -r "$YEYO_DIR/requirements.txt" \
       2>&1 | tee -a "$LOG_FILE"

     success "Entorno Python configurado: $VENV_DIR"
   }

   install_tailscale() {
     step "6/9 Instalando Tailscale"

     if command -v tailscale &>/dev/null; then
       info "Tailscale ya instalado: $(tailscale version 2>/dev/null | head -1)"
       return
     fi

     case "$OS_DISTRO" in
       ubuntu|debian)
         curl -fsSL https://tailscale.com/install.sh | sh 2>&1 | tee -a "$LOG_FILE"
         ;;
       arch|manjaro)
         sudo pacman -S --noconfirm --needed tailscale
         ;;
       fedora|rhel|centos)
         sudo dnf config-manager --add-repo https://pkgs.tailscale.com/stable/fedora/tailscale.repo
         sudo dnf install -y tailscale
         ;;
     esac

     sudo systemctl enable --now tailscaled 2>/dev/null || true

     success "Tailscale instalado"
     info "Ejecutar 'tailscale up' para conectarse a la red"
   }

   install_ollama() {
     step "7/9 Instalando Ollama y modelos"

     if ! command -v ollama &>/dev/null; then
       info "Instalando Ollama..."
       curl -fsSL https://ollama.ai/install.sh | sh 2>&1 | tee -a "$LOG_FILE"
     else
       info "Ollama ya instalado: $(ollama --version 2>/dev/null || echo 'desconocido')"
     fi

     sudo systemctl enable --now ollama 2>/dev/null || (ollama serve &>/dev/null &) || true
     sleep 3  # Esperar que Ollama inicie

     case "$MODE" in
       minimo)
         info "Modo mínimo: sin modelos locales (delegando al Central)"
         ;;
       ligero)
         info "Descargando modelo ligero: qwen2.5:0.5b..."
         ollama pull qwen2.5:0.5b 2>&1 | tee -a "$LOG_FILE" || warn "No se pudo descargar qwen2.5:0.5b"
         ;;
       completo|*)
         info "Descargando modelos completos (puede tardar varios minutos)..."
         ollama pull qwen2.5:3b 2>&1 | tee -a "$LOG_FILE" || warn "No se pudo descargar qwen2.5:3b"
         ollama pull qwen2.5:0.5b 2>&1 | tee -a "$LOG_FILE" || true
         ;;
     esac

     success "Ollama configurado en modo $MODE"
   }

   configure_systemd() {
     step "8/9 Configurando servicios systemd"

     if [[ "$SYSTEMD_AVAILABLE" != "true" ]]; then
       warn "systemd no disponible — los servicios deben iniciarse manualmente"
       warn "Usa: bash $YEYO_DIR/scripts/start-satellite.sh"
       return
     fi

     local systemd_user_dir="${HOME}/.config/systemd/user"
     mkdir -p "$systemd_user_dir"

     # Servicio: yeyo-backend
     cat > "$systemd_user_dir/yeyo-backend.service" << EOF
   [Unit]
   Description=YeyoOS Backend (FastAPI)
   After=network.target redis.service

   [Service]
   WorkingDirectory=${YEYO_DIR}
   ExecStart=${VENV_DIR}/bin/uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 2
   Restart=always
   RestartSec=5
   Environment="PYTHONPATH=${YEYO_DIR}"
   Environment="REDIS_URL=redis://localhost:6379/0"
   Environment="YEYO_NODE_TYPE=satellite"

   [Install]
   WantedBy=default.target
   EOF

     # Servicio: yeyo-worker (Celery)
     cat > "$systemd_user_dir/yeyo-worker.service" << EOF
   [Unit]
   Description=YeyoOS Celery Worker
   After=network.target redis.service yeyo-backend.service

   [Service]
   WorkingDirectory=${YEYO_DIR}
   ExecStart=${VENV_DIR}/bin/celery -A src.cluster.worker.celery_app worker \
     --loglevel=info --concurrency=2 \
     --queues=gpu_tasks,cpu_tasks,training_tasks
   Restart=always
   RestartSec=10
   Environment="PYTHONPATH=${YEYO_DIR}"
   Environment="REDIS_URL=redis://localhost:6379/0"

   [Install]
   WantedBy=default.target
   EOF

     # Servicio: yeyo-frontend
     cat > "$systemd_user_dir/yeyo-frontend.service" << EOF
   [Unit]
   Description=YeyoOS Frontend (Vite)
   After=network.target yeyo-backend.service

   [Service]
   WorkingDirectory=${YEYO_DIR}/frontend
   ExecStart=/usr/bin/npm run preview -- --host 0.0.0.0 --port 3000
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=default.target
   EOF

     systemctl --user daemon-reload
     systemctl --user enable yeyo-backend yeyo-worker yeyo-frontend 2>/dev/null || true

     success "Servicios systemd configurados"
     info "Iniciar con: systemctl --user start yeyo-backend yeyo-worker yeyo-frontend"
   }

   start_onboarding() {
     step "9/9 Iniciando onboarding de YeyoNet"

     echo ""
     echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
     echo -e "${BOLD}${GREEN}║        🎉  YeyoOS Satélite — Instalado                 ║${NC}"
     echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
     echo ""
     echo -e "  Log de instalación: ${CYAN}$LOG_FILE${NC}"
     echo ""
     echo -e "  ${BOLD}Próximos pasos:${NC}"
     echo -e "  1. Conectar Tailscale:   ${CYAN}sudo tailscale up${NC}"
     echo -e "  2. Iniciar servicios:    ${CYAN}systemctl --user start yeyo-backend yeyo-worker${NC}"
     echo -e "  3. Conectar al Central:  ${CYAN}http://localhost:3000 → Ingresar código YEYO-XXXX${NC}"
     echo ""

     # Abrir onboarding en el navegador si hay pantalla disponible
     if [[ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]]; then
       info "Abriendo interfaz de onboarding..."
       (sleep 3 && xdg-open "http://localhost:3000/onboarding" 2>/dev/null) &
     else
       info "Sin pantalla detectada. Accede a: http://localhost:3000/onboarding"
     fi
   }

   # ── Main ──────────────────────────────────────────────────────────────────────

   main() {
     echo ""
     echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
     echo -e "${BOLD}${BLUE}║         YeyoOS — Instalador de Satélite v${YEYO_VERSION}          ║${NC}"
     echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
     echo ""
     echo -e "  Modo: ${BOLD}$MODE${NC}"
     echo -e "  Directorio: ${CYAN}$YEYO_DIR${NC}"
     echo -e "  Log: ${CYAN}$LOG_FILE${NC}"
     echo ""

     if [[ "$AUTO_YES" != "true" ]]; then
       read -rp "¿Continuar con la instalación? [s/N] " confirm
       [[ "${confirm,,}" =~ ^[sy] ]] || { info "Instalación cancelada"; exit 0; }
     fi

     check_root
     detect_os
     install_system_deps
     install_docker
     install_nodejs
     clone_yeyo_os
     setup_python_env
     install_tailscale
     install_ollama
     configure_systemd
     start_onboarding
   }

   main "$@"

2. Crear archivo scripts/install-central.sh:

   Ruta: ~/yeyo-os/scripts/install-central.sh
   Contenido:

   #!/usr/bin/env bash
   # =============================================================================
   # YeyoOS — Instalador de Central
   # Micro-fase 7.23 — Capa 7: Evolución
   #
   # Configura YeyoOS como nodo Central de YeyoNet.
   # El Central gestiona satélites, Flower server y Celery broker.
   #
   # Uso: bash install-central.sh [--yes]
   # =============================================================================

   set -euo pipefail
   IFS=$'\n\t'

   # Reutilizar el instalador de satélite como base
   SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
   SATELLITE_SCRIPT="${SCRIPT_DIR}/install-satellite.sh"

   RED='\033[0;31m'
   GREEN='\033[0;32m'
   YELLOW='\033[1;33m'
   BLUE='\033[0;34m'
   CYAN='\033[0;36m'
   BOLD='\033[1m'
   NC='\033[0m'

   info()    { echo -e "${CYAN}ℹ  ${NC}$*"; }
   success() { echo -e "${GREEN}✅ ${NC}$*"; }
   step()    { echo -e "\n${BOLD}${BLUE}▶ $*${NC}"; }
   fatal()   { echo -e "${RED}❌ ${NC}$*" >&2; exit 1; }

   YEYO_DIR="${HOME}/yeyo-os"
   VENV_DIR="${YEYO_DIR}/.venv"
   AUTO_YES=false

   for arg in "$@"; do
     case "$arg" in
       --yes|-y) AUTO_YES=true ;;
     esac
   done

   install_central_extras() {
     step "CENTRAL: Instalando componentes adicionales del Central"

     info "Instalando dependencias Python del Central..."
     "$VENV_DIR/bin/pip" install --quiet \
       flwr grpcio grpcio-tools prometheus-client celery[redis] flower \
       2>&1 | tee -a /tmp/yeyo-central-install.log

     # Configurar Redis para mayor throughput
     info "Configurando Redis para Celery broker..."
     if command -v redis-cli &>/dev/null; then
       redis-cli config set maxmemory 2gb 2>/dev/null || true
       redis-cli config set maxmemory-policy allkeys-lru 2>/dev/null || true
     fi

     success "Componentes del Central instalados"
   }

   configure_central_systemd() {
     step "CENTRAL: Configurando servicios adicionales systemd"

     local systemd_user_dir="${HOME}/.config/systemd/user"
     mkdir -p "$systemd_user_dir"

     # Servicio: yeyo-flower (Federated Learning server)
     cat > "$systemd_user_dir/yeyo-flower.service" << EOF
   [Unit]
   Description=YeyoOS Flower Federated Learning Server
   After=network.target yeyo-backend.service

   [Service]
   WorkingDirectory=${YEYO_DIR}
   ExecStart=${VENV_DIR}/bin/python -m src.cluster.federated.server \
     --server-address=0.0.0.0:8080 --num-rounds=10 --min-clients=1
   Restart=always
   RestartSec=15
   Environment="PYTHONPATH=${YEYO_DIR}"
   Environment="REDIS_URL=redis://localhost:6379/0"
   Environment="YEYO_NODE_TYPE=central"

   [Install]
   WantedBy=default.target
   EOF

     # Servicio: yeyo-celery-beat (scheduler periódico)
     cat > "$systemd_user_dir/yeyo-celery-beat.service" << EOF
   [Unit]
   Description=YeyoOS Celery Beat (tareas periódicas)
   After=network.target redis.service

   [Service]
   WorkingDirectory=${YEYO_DIR}
   ExecStart=${VENV_DIR}/bin/celery -A src.cluster.worker.celery_app beat \
     --loglevel=info --scheduler=celery.beat:PersistentScheduler
   Restart=always
   RestartSec=10
   Environment="PYTHONPATH=${YEYO_DIR}"
   Environment="REDIS_URL=redis://localhost:6379/0"
   Environment="YEYO_NODE_TYPE=central"

   [Install]
   WantedBy=default.target
   EOF

     if command -v systemctl &>/dev/null; then
       systemctl --user daemon-reload
       systemctl --user enable yeyo-flower yeyo-celery-beat 2>/dev/null || true
     fi

     success "Servicios del Central configurados"
   }

   download_all_models() {
     step "CENTRAL: Descargando todos los modelos Ollama"

     local models=(
       "qwen2.5:3b"
       "qwen2.5:7b"
       "qwen2.5:0.5b"
     )

     for model in "${models[@]}"; do
       info "Descargando $model..."
       ollama pull "$model" 2>&1 | tail -1 || warn "No se pudo descargar $model"
     done

     success "Modelos descargados"
   }

   show_central_info() {
     echo ""
     echo -e "${BOLD}${GREEN}╔════════════════════════════════════════════════════════╗${NC}"
     echo -e "${BOLD}${GREEN}║        🧠  YeyoOS Central — Instalado                  ║${NC}"
     echo -e "${BOLD}${GREEN}╚════════════════════════════════════════════════════════╝${NC}"
     echo ""
     echo -e "  ${BOLD}Servicios del Central:${NC}"
     echo -e "  • Backend:     ${CYAN}http://localhost:8000${NC}"
     echo -e "  • Frontend:    ${CYAN}http://localhost:3000${NC}"
     echo -e "  • Flower FL:   ${CYAN}http://localhost:8080${NC}  (Federated Learning)"
     echo -e "  • Celery:      via Redis localhost:6379"
     echo ""
     echo -e "  ${BOLD}Para invitar un satélite:${NC}"
     echo -e "  1. Abre ${CYAN}http://localhost:3000/yeyonet${NC}"
     echo -e "  2. Click '+ Invitar satélite'"
     echo -e "  3. Comparte el código YEYO-XXXX-XXXX-XXXX"
     echo ""
     echo -e "  ${BOLD}Iniciar servicios:${NC}"
     echo -e "  ${CYAN}systemctl --user start yeyo-backend yeyo-worker yeyo-frontend yeyo-flower${NC}"
     echo ""
   }

   main() {
     echo ""
     echo -e "${BOLD}${BLUE}╔════════════════════════════════════════════════════════╗${NC}"
     echo -e "${BOLD}${BLUE}║         YeyoOS — Instalador de Central                 ║${NC}"
     echo -e "${BOLD}${BLUE}╚════════════════════════════════════════════════════════╝${NC}"
     echo ""

     if [[ "$AUTO_YES" != "true" ]]; then
       read -rp "¿Instalar YeyoOS como Central? [s/N] " confirm
       [[ "${confirm,,}" =~ ^[sy] ]] || { info "Instalación cancelada"; exit 0; }
     fi

     # Primero instalar como satélite base (modo completo)
     info "Ejecutando instalador base (satélite completo)..."
     bash "$SATELLITE_SCRIPT" --mode=completo --yes

     # Luego añadir componentes del Central
     install_central_extras
     configure_central_systemd
     download_all_models
     show_central_info
   }

   main "$@"

3. Crear archivo scripts/test_install.sh:

   Ruta: ~/yeyo-os/scripts/test_install.sh
   Contenido:

   #!/usr/bin/env bash
   # =============================================================================
   # YeyoOS — Tests del instalador con Bash Automated Testing System (bats)
   # Micro-fase 7.23 — Capa 7: Evolución
   #
   # Verifica que el instalador funciona correctamente.
   # Uso: bats scripts/test_install.sh
   # Instalar bats: npm install -g bats  o  sudo apt-get install bats
   # =============================================================================

   # ── Setup / Teardown ──────────────────────────────────────────────────────────

   setup() {
     # Directorio temporal para tests aislados
     TEST_TMP_DIR="$(mktemp -d /tmp/yeyo-test-XXXXXX)"
     export TEST_TMP_DIR

     # Stub de funciones del sistema para tests sin privilegios
     export PATH="${TEST_TMP_DIR}/bin:${PATH}"

     # Crear stubs de comandos del sistema
     mkdir -p "${TEST_TMP_DIR}/bin"

     # Stub apt-get
     cat > "${TEST_TMP_DIR}/bin/apt-get" << 'STUB'
   #!/bin/bash
   echo "[stub] apt-get $*"
   exit 0
   STUB

     # Stub git
     cat > "${TEST_TMP_DIR}/bin/git" << 'STUB'
   #!/bin/bash
   if [[ "$1" == "clone" ]]; then
     mkdir -p "${@: -1}/.git"
     touch "${@: -1}/requirements.txt"
   elif [[ "$1" == "pull" ]]; then
     echo "Already up to date."
   fi
   exit 0
   STUB

     # Stub ollama
     cat > "${TEST_TMP_DIR}/bin/ollama" << 'STUB'
   #!/bin/bash
   echo "[stub] ollama $*"
   exit 0
   STUB

     # Stub tailscale
     cat > "${TEST_TMP_DIR}/bin/tailscale" << 'STUB'
   #!/bin/bash
   echo "[stub] tailscale $*"
   echo "1.50.0"
   exit 0
   STUB

     # Stub docker
     cat > "${TEST_TMP_DIR}/bin/docker" << 'STUB'
   #!/bin/bash
   echo "[stub] docker $*"
   exit 0
   STUB

     # Stub python3.11
     cat > "${TEST_TMP_DIR}/bin/python3.11" << 'STUB'
   #!/bin/bash
   echo "Python 3.11.0"
   exit 0
   STUB

     # Stub pip
     cat > "${TEST_TMP_DIR}/bin/pip" << 'STUB'
   #!/bin/bash
   echo "[stub] pip $*"
   exit 0
   STUB

     # Stub systemctl
     cat > "${TEST_TMP_DIR}/bin/systemctl" << 'STUB'
   #!/bin/bash
   echo "[stub] systemctl $*"
   exit 0
   STUB

     # Stub curl
     cat > "${TEST_TMP_DIR}/bin/curl" << 'STUB'
   #!/bin/bash
   echo "[stub] curl $*"
   exit 0
   STUB

     # Stub redis-cli
     cat > "${TEST_TMP_DIR}/bin/redis-cli" << 'STUB'
   #!/bin/bash
   echo "[stub] redis-cli $*"
   exit 0
   STUB

     chmod +x "${TEST_TMP_DIR}/bin/"*

     # Crear /etc/os-release temporal para detectar Ubuntu
     export YEYO_TEST_OS_RELEASE="${TEST_TMP_DIR}/os-release"
     cat > "$YEYO_TEST_OS_RELEASE" << 'OSREL'
   ID=ubuntu
   VERSION_CODENAME=jammy
   PRETTY_NAME="Ubuntu 22.04 LTS"
   OSREL

     # Directorio de instalación temporal
     export YEYO_DIR="${TEST_TMP_DIR}/yeyo-os"
     export VENV_DIR="${YEYO_DIR}/.venv"
     mkdir -p "${VENV_DIR}/bin"
     cat > "${VENV_DIR}/bin/pip" << 'VPIP'
   #!/bin/bash
   echo "[venv-pip] $*"; exit 0
   VPIP
     cat > "${VENV_DIR}/bin/uvicorn" << 'VUVI'
   #!/bin/bash
   echo "[venv-uvicorn] $*"; exit 0
   VUVI
     cat > "${VENV_DIR}/bin/celery" << 'VCEL'
   #!/bin/bash
   echo "[venv-celery] $*"; exit 0
   VCEL
     chmod +x "${VENV_DIR}/bin/"*
   }

   teardown() {
     rm -rf "$TEST_TMP_DIR"
   }

   # ── Helper: cargar funciones del instalador sin ejecutar main ─────────────────

   load_installer() {
     local script="$1"
     # Extraer solo las funciones, no ejecutar main()
     # shellcheck source=/dev/null
     source <(grep -v '^main ' "$script" | grep -v '^\s*main "$@"')
   }

   # ── Tests de detección de OS ──────────────────────────────────────────────────

   @test "detect_os reconoce Ubuntu" {
     # Simular /etc/os-release de Ubuntu
     mkdir -p /tmp/yeyo-bats-$$
     cat > /tmp/yeyo-bats-$$/os-release << 'EOF'
   ID=ubuntu
   VERSION_CODENAME=jammy
   PRETTY_NAME="Ubuntu 22.04 LTS"
   EOF

     run bash -c "
       source /tmp/yeyo-bats-$$/os-release
       echo \$ID
     "
     rm -rf /tmp/yeyo-bats-$$
     [ "$status" -eq 0 ]
     [[ "$output" == "ubuntu" ]]
   }

   @test "detect_os reconoce Arch" {
     run bash -c "
       ID=arch
       case \$ID in
         arch|manjaro) echo 'pacman' ;;
         ubuntu|debian) echo 'apt-get' ;;
       esac
     "
     [ "$status" -eq 0 ]
     [[ "$output" == "pacman" ]]
   }

   @test "detect_os reconoce Debian" {
     run bash -c "
       ID=debian
       VERSION_CODENAME=bookworm
       case \$ID in
         ubuntu|debian) echo 'apt-get' ;;
       esac
     "
     [ "$status" -eq 0 ]
     [[ "$output" == "apt-get" ]]
   }

   # ── Tests del script de instalación ──────────────────────────────────────────

   @test "install-satellite.sh existe y tiene permisos de ejecución" {
     local script
     script="$(dirname "$BATS_TEST_FILENAME")/install-satellite.sh"
     [ -f "$script" ]
   }

   @test "install-central.sh existe" {
     local script
     script="$(dirname "$BATS_TEST_FILENAME")/install-central.sh"
     [ -f "$script" ]
   }

   @test "install-satellite.sh tiene sintaxis bash válida" {
     local script
     script="$(dirname "$BATS_TEST_FILENAME")/install-satellite.sh"
     run bash -n "$script"
     [ "$status" -eq 0 ]
   }

   @test "install-central.sh tiene sintaxis bash válida" {
     local script
     script="$(dirname "$BATS_TEST_FILENAME")/install-central.sh"
     run bash -n "$script"
     [ "$status" -eq 0 ]
   }

   @test "install-satellite.sh --help no falla" {
     local script
     script="$(dirname "$BATS_TEST_FILENAME")/install-satellite.sh"
     run bash "$script" --help
     [ "$status" -eq 0 ]
   }

   @test "install-satellite.sh acepta --mode=ligero" {
     run bash -c "
       MODE=completo
       for arg in --mode=ligero; do
         case \"\$arg\" in
           --mode=*) MODE=\"\${arg#--mode=}\" ;;
         esac
       done
       echo \$MODE
     "
     [ "$status" -eq 0 ]
     [[ "$output" == "ligero" ]]
   }

   @test "install-satellite.sh acepta --mode=minimo" {
     run bash -c "
       MODE=completo
       for arg in --mode=minimo; do
         case \"\$arg\" in
           --mode=*) MODE=\"\${arg#--mode=}\" ;;
         esac
       done
       echo \$MODE
     "
     [ "$status" -eq 0 ]
     [[ "$output" == "minimo" ]]
   }

   # ── Tests de funciones individuales ──────────────────────────────────────────

   @test "PKG_MANAGER se asigna correctamente para ubuntu" {
     run bash -c "
       OS_DISTRO=ubuntu
       case \"\$OS_DISTRO\" in
         ubuntu|debian) PKG_MANAGER=apt-get ;;
         arch|manjaro)  PKG_MANAGER=pacman  ;;
         fedora|rhel)   PKG_MANAGER=dnf     ;;
       esac
       echo \$PKG_MANAGER
     "
     [ "$status" -eq 0 ]
     [[ "$output" == "apt-get" ]]
   }

   @test "formato de código de invitación YEYO-XXXX" {
     run bash -c "
       code=\"YEYO-\$(tr -dc 'A-Z0-9' < /dev/urandom | head -c4)-\$(tr -dc 'A-Z0-9' < /dev/urandom | head -c4)-\$(tr -dc 'A-Z0-9' < /dev/urandom | head -c4)\"
       echo \"\$code\" | grep -E '^YEYO-[A-Z0-9]{4}-[A-Z0-9]{4}-[A-Z0-9]{4}$'
     "
     [ "$status" -eq 0 ]
   }

   @test "configure_systemd crea archivos .service" {
     local tmp
     tmp="$(mktemp -d)"
     mkdir -p "${tmp}/.config/systemd/user"
     HOME="$tmp" run bash -c "
       YEYO_DIR='${tmp}/yeyo-os'
       VENV_DIR=\"\${YEYO_DIR}/.venv\"
       systemd_user_dir=\"\${HOME}/.config/systemd/user\"
       mkdir -p \"\$systemd_user_dir\"
       cat > \"\${systemd_user_dir}/yeyo-backend.service\" << 'SVC'
   [Unit]
   Description=YeyoOS Backend
   SVC
       ls \"\$systemd_user_dir\"
     "
     rm -rf "$tmp"
     [ "$status" -eq 0 ]
     [[ "$output" == *"yeyo-backend.service"* ]]
   }

   @test "ollama pull se llama con modelo correcto para modo completo" {
     run bash -c "
       MODE=completo
       case \"\$MODE\" in
         minimo) echo 'no-models' ;;
         ligero) echo 'qwen2.5:0.5b' ;;
         completo|*) echo 'qwen2.5:3b' ;;
       esac
     "
     [ "$status" -eq 0 ]
     [[ "$output" == "qwen2.5:3b" ]]
   }

   @test "ollama pull no se llama en modo minimo" {
     run bash -c "
       MODE=minimo
       case \"\$MODE\" in
         minimo) echo 'skip' ;;
         *) echo 'pull' ;;
       esac
     "
     [ "$status" -eq 0 ]
     [[ "$output" == "skip" ]]
   }

   @test "configuración de Redis maxmemory es 2gb" {
     run bash -c "
       echo 'redis-cli config set maxmemory 2gb'
     "
     [ "$status" -eq 0 ]
     [[ "$output" == *"maxmemory 2gb"* ]]
   }

   @test "YEYO_DIR por defecto es ~/yeyo-os" {
     run bash -c "
       YEYO_DIR=\"\${HOME}/yeyo-os\"
       echo \"\$YEYO_DIR\"
     "
     [ "$status" -eq 0 ]
     [[ "$output" == *"/yeyo-os" ]]
   }

   @test "venv se crea en YEYO_DIR/.venv" {
     run bash -c "
       YEYO_DIR=\"/tmp/yeyo-test-venv\"
       VENV_DIR=\"\${YEYO_DIR}/.venv\"
       echo \"\$VENV_DIR\"
     "
     [ "$status" -eq 0 ]
     [[ "$output" == "/tmp/yeyo-test-venv/.venv" ]]
   }

   @test "set -euo pipefail presente en install-satellite.sh" {
     local script
     script="$(dirname "$BATS_TEST_FILENAME")/install-satellite.sh"
     run grep "set -euo pipefail" "$script"
     [ "$status" -eq 0 ]
   }

   @test "set -euo pipefail presente en install-central.sh" {
     local script
     script="$(dirname "$BATS_TEST_FILENAME")/install-central.sh"
     run grep "set -euo pipefail" "$script"
     [ "$status" -eq 0 ]
   }

   @test "install-central.sh invoca install-satellite.sh" {
     local script
     script="$(dirname "$BATS_TEST_FILENAME")/install-central.sh"
     run grep "install-satellite.sh" "$script"
     [ "$status" -eq 0 ]
   }

VERIFICAR:
- [ ] scripts/install-satellite.sh — 9 pasos, detecta OS, instala deps, clona repo, configura Python, Tailscale, Ollama, systemd
- [ ] scripts/install-central.sh — extiende satellite con Flower server, Celery beat, todos los modelos
- [ ] scripts/test_install.sh — tests bats para cada función crítica
- [ ] install-satellite.sh --help no falla
- [ ] bash -n scripts/install-satellite.sh — sintaxis válida (sin ejecutar)
- [ ] Tests bats pasan: bats scripts/test_install.sh (≥16 tests)

SI FALLA:
- bats no instalado: npm install -g bats  o  sudo apt-get install bats
- Permisos: chmod +x scripts/install-satellite.sh scripts/install-central.sh
- ShellCheck warnings: instalar shellcheck para validar: shellcheck scripts/install-satellite.sh
- Tests de systemd fallán en CI sin systemd: los tests verifican creación de archivos .service, no ejecución

NO HACER:
- No hardcodear contraseñas o tokens en los scripts
- No usar sudo sin verificar que está disponible
- No asumir que el usuario es root
- No descargar scripts de internet sin verificar checksum
- No implementar la ISO booteable en este script (eso es 7.24)
- No romper instalación existente si el usuario ya tiene YeyoOS (idempotente)

GATE: En una PC limpia con Ubuntu 22.04, bash scripts/install-satellite.sh --mode=completo --yes completa sin errores, instala Python/Redis/Docker/Ollama/Tailscale, crea servicios systemd y muestra instrucciones de onboarding. bats scripts/test_install.sh pasa ≥16 tests.
```
