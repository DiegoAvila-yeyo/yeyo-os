## ═══════════════════════════════════════
## MICRO-FASE 0.7 — Rust Toolchain
## Tipo: CLI | Prompts: 1 | Complejidad: Simple
## ═══════════════════════════════════════

### PROMPT 0.7-1 [CLI] — Instalar Rust y crear proyecto Guardian

```
Estamos construyendo YeyoOS. Micro-fase 0.7: instalar Rust toolchain para el compositor Wayland (Capa 3) y Guardian daemon (Capa 6).

Entorno: WSL2 Ubuntu. Micro-fases 0.0-0.6 completadas.

EJECUTAR:
1. Instalar Rust via rustup:
   curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
   source $HOME/.cargo/env

2. Instalar componentes adicionales:
   rustup component add clippy rustfmt
   rustup target add x86_64-unknown-linux-gnu

3. Instalar dependencias de sistema para compilación:
   sudo apt install -y cmake libwayland-dev libxkbcommon-dev libudev-dev libinput-dev libgbm-dev libdrm-dev

4. Crear workspace Rust dentro del proyecto:
   cd ~/yeyo-os
   mkdir -p rust/
   cd rust/
   
   Crear Cargo.toml de workspace:
   [workspace]
   members = ["guardian", "compositor"]
   resolver = "2"

5. Crear proyecto Guardian (scaffold):
   cargo init guardian --name yeyo-guardian
   cd guardian
   cargo add tokio --features full
   cargo add serde serde_json --features derive
   cargo add chrono --features serde
   cd ..

6. Crear proyecto Compositor (scaffold vacío):
   cargo init compositor --name yeyo-compositor
   cd ..

7. Verificar que compila:
   cd rust && cargo build

VERIFICAR:
- [ ] Rust version: `rustc --version` → 1.7x.x+
- [ ] Cargo version: `cargo --version`
- [ ] Clippy funciona: `cd ~/yeyo-os/rust && cargo clippy` → sin errores
- [ ] Guardian compila: `cargo build -p yeyo-guardian` → OK
- [ ] Compositor compila: `cargo build -p yeyo-compositor` → OK
- [ ] Workspace build: `cargo build` → ambos compilan

SI FALLA:
- Rustup no en PATH: `source $HOME/.cargo/env` o agregar a ~/.bashrc
- Dependencias de sistema faltantes: instalar lo que pida el error de compilación
- WSL2 sin wayland libs: las instalamos para compilar, no para ejecutar aún

NO HACER:
- No implementar lógica en Guardian aún (Capa 6)
- No implementar compositor aún (Capa 3)
- Solo scaffold + verificar que compila

GATE: Rust + cargo funcionando, workspace con 2 proyectos (guardian + compositor), ambos compilan.
```
