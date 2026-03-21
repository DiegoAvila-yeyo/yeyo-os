## ═══════════════════════════════════════
## MICRO-FASE 7.6 — ISO Verification
## Tipo: CLI | Prompts: 2 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.6-2 [CLI] — Crear tests de verificación de ISO

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.6 (parte 2) de Capa 7 (Evolución): crear tests automatizados para verificar que la ISO generada es correcta y bootable.

CONTEXTO:
- Micro-fase 7.6-1 completada: ISO Builder creado
- Necesitamos verificar: ISO válida, bootable en QEMU, tamaño correcto, paquetes incluidos
- Verificación UEFI vía OVMF firmware en QEMU
- Tests automatizados para CI/CD
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre un terminal.

CREAR:

1. Crear archivo scripts/iso/verify_iso.sh:

   Ruta: ~/yeyo-os/scripts/iso/verify_iso.sh
   Contenido:

   #!/bin/bash
   # ═══════════════════════════════════════
   # YeyoOS — ISO Verification
   # Micro-fase 7.6 — Capa 7: Evolución
   #
   # Verifica integridad y bootabilidad de la ISO.
   # Uso: ./verify_iso.sh <path-to-iso>
   # ═══════════════════════════════════════

   set -euo pipefail

   ISO_PATH="${1:-}"
   RESULTS_FILE="/tmp/yeyo-iso-verify-results.json"
   PASSED=0
   FAILED=0
   TOTAL=0

   check() {
       local name="$1"
       local result="$2"
       TOTAL=$((TOTAL + 1))
       if [ "$result" = "pass" ]; then
           PASSED=$((PASSED + 1))
           echo "  ✅ ${name}"
       else
           FAILED=$((FAILED + 1))
           echo "  ❌ ${name}"
       fi
   }

   if [ -z "$ISO_PATH" ]; then
       echo "Uso: $0 <path-to-iso>"
       exit 1
   fi

   if [ ! -f "$ISO_PATH" ]; then
       echo "ERROR: ISO no encontrada: $ISO_PATH"
       exit 1
   fi

   echo "═══════════════════════════════════════"
   echo " YeyoOS ISO Verification"
   echo "═══════════════════════════════════════"
   echo " ISO: ${ISO_PATH}"
   echo ""

   # --- Test 1: Archivo existe y tiene tamaño razonable ---
   echo "[Test 1] Verificando archivo ISO..."
   ISO_SIZE=$(stat -c%s "$ISO_PATH" 2>/dev/null || stat -f%z "$ISO_PATH" 2>/dev/null)
   ISO_SIZE_MB=$((ISO_SIZE / 1024 / 1024))

   check "ISO existe" "pass"

   if [ "$ISO_SIZE_MB" -ge 500 ] && [ "$ISO_SIZE_MB" -le 6000 ]; then
       check "Tamaño razonable (${ISO_SIZE_MB}MB, esperado 500-6000MB)" "pass"
   else
       check "Tamaño razonable (${ISO_SIZE_MB}MB, esperado 500-6000MB)" "fail"
   fi

   # --- Test 2: Verificar integridad con metadata ---
   echo "[Test 2] Verificando integridad..."
   META_FILE="${ISO_PATH}.meta.json"
   if [ -f "$META_FILE" ]; then
       EXPECTED_SHA=$(python3 -c "import json; print(json.load(open('${META_FILE}'))['sha256'])")
       ACTUAL_SHA=$(sha256sum "$ISO_PATH" | cut -d' ' -f1)
       if [ "$EXPECTED_SHA" = "$ACTUAL_SHA" ]; then
           check "SHA256 coincide" "pass"
       else
           check "SHA256 coincide (expected: ${EXPECTED_SHA:0:16}... got: ${ACTUAL_SHA:0:16}...)" "fail"
       fi
   else
       check "Metadata disponible" "fail"
   fi

   # --- Test 3: Verificar estructura ISO ---
   echo "[Test 3] Verificando estructura ISO..."
   MOUNT_DIR="/tmp/yeyo-iso-mount"
   mkdir -p "$MOUNT_DIR"

   if mount -o loop,ro "$ISO_PATH" "$MOUNT_DIR" 2>/dev/null; then
       # Verificar archivos esenciales
       [ -f "${MOUNT_DIR}/live/vmlinuz" ] && check "Kernel presente" "pass" || check "Kernel presente" "fail"
       [ -f "${MOUNT_DIR}/live/initrd.img" ] && check "Initrd presente" "pass" || check "Initrd presente" "fail"
       [ -f "${MOUNT_DIR}/live/filesystem.squashfs" ] && check "Filesystem squashfs presente" "pass" || check "Filesystem squashfs presente" "fail"
       [ -f "${MOUNT_DIR}/boot/grub/grub.cfg" ] && check "GRUB config presente" "pass" || check "GRUB config presente" "fail"

       # Verificar GRUB config
       if grep -q "YeyoOS" "${MOUNT_DIR}/boot/grub/grub.cfg" 2>/dev/null; then
           check "GRUB config menciona YeyoOS" "pass"
       else
           check "GRUB config menciona YeyoOS" "fail"
       fi

       # Verificar recovery mode en GRUB
       if grep -q "Recovery" "${MOUNT_DIR}/boot/grub/grub.cfg" 2>/dev/null; then
           check "Recovery mode en GRUB" "pass"
       else
           check "Recovery mode en GRUB" "fail"
       fi

       umount "$MOUNT_DIR" 2>/dev/null || true
   else
       check "Montaje ISO (requiere root)" "fail"
   fi

   rmdir "$MOUNT_DIR" 2>/dev/null || true

   # --- Test 4: Verificar bootabilidad con QEMU (si disponible) ---
   echo "[Test 4] Test de boot con QEMU..."
   if command -v qemu-system-x86_64 &>/dev/null; then
       # Boot test con timeout (verifica que GRUB carga)
       QEMU_LOG="/tmp/yeyo-qemu-boot.log"
       timeout 30 qemu-system-x86_64 \
           -cdrom "$ISO_PATH" \
           -m 2048 \
           -nographic \
           -serial file:"$QEMU_LOG" \
           -no-reboot \
           2>/dev/null &
       QEMU_PID=$!
       sleep 15
       kill $QEMU_PID 2>/dev/null || true
       wait $QEMU_PID 2>/dev/null || true

       if [ -f "$QEMU_LOG" ] && [ -s "$QEMU_LOG" ]; then
           check "QEMU boot produce output" "pass"
       else
           check "QEMU boot produce output" "fail"
       fi
       rm -f "$QEMU_LOG"

       # UEFI boot test (si OVMF disponible)
       OVMF_PATH="/usr/share/OVMF/OVMF_CODE.fd"
       if [ -f "$OVMF_PATH" ]; then
           QEMU_LOG_UEFI="/tmp/yeyo-qemu-uefi.log"
           timeout 30 qemu-system-x86_64 \
               -cdrom "$ISO_PATH" \
               -m 2048 \
               -bios "$OVMF_PATH" \
               -nographic \
               -serial file:"$QEMU_LOG_UEFI" \
               -no-reboot \
               2>/dev/null &
           QEMU_PID=$!
           sleep 15
           kill $QEMU_PID 2>/dev/null || true
           wait $QEMU_PID 2>/dev/null || true

           if [ -f "$QEMU_LOG_UEFI" ] && [ -s "$QEMU_LOG_UEFI" ]; then
               check "UEFI boot con OVMF produce output" "pass"
           else
               check "UEFI boot con OVMF produce output" "fail"
           fi
           rm -f "$QEMU_LOG_UEFI"
       else
           echo "  ⏭️  OVMF no disponible, saltando test UEFI"
       fi
   else
       echo "  ⏭️  QEMU no disponible, saltando tests de boot"
   fi

   # --- Resultado ---
   echo ""
   echo "═══════════════════════════════════════"
   echo " Resultados: ${PASSED}/${TOTAL} passed, ${FAILED} failed"
   echo "═══════════════════════════════════════"

   # Guardar resultados
   cat > "$RESULTS_FILE" <<EOF
   {
     "iso_path": "${ISO_PATH}",
     "iso_size_mb": ${ISO_SIZE_MB},
     "total_checks": ${TOTAL},
     "passed": ${PASSED},
     "failed": ${FAILED},
     "verified_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
   }
   EOF
   echo "Resultados guardados en: ${RESULTS_FILE}"

   if [ "$FAILED" -gt 0 ]; then
       exit 1
   fi
   exit 0

2. Hacer ejecutable:
   chmod +x scripts/iso/verify_iso.sh

3. Crear archivo tests/iso/test_iso_structure.py:

   Ruta: ~/yeyo-os/tests/iso/test_iso_structure.py
   Contenido:

   """
   Tests para ISO Builder — Micro-fase 7.6
   Verifica la estructura y configuración del build script.
   """

   import os
   import json
   import pytest
   from pathlib import Path


   class TestISOBuildScript:
       """Tests para el script de build ISO."""

       def test_build_script_exists(self):
           assert Path("scripts/iso/build_iso.sh").exists()

       def test_build_script_executable(self):
           assert os.access("scripts/iso/build_iso.sh", os.X_OK)

       def test_verify_script_exists(self):
           assert Path("scripts/iso/verify_iso.sh").exists()

       def test_verify_script_executable(self):
           assert os.access("scripts/iso/verify_iso.sh", os.X_OK)

       def test_build_script_has_grub_config(self):
           content = Path("scripts/iso/build_iso.sh").read_text()
           assert "grub.cfg" in content
           assert "YeyoOS" in content

       def test_build_script_has_systemd_services(self):
           content = Path("scripts/iso/build_iso.sh").read_text()
           assert "ollama.service" in content
           assert "yeyo-os.service" in content
           assert "yeyo-guardian.service" in content

       def test_build_script_uses_btrfs(self):
           content = Path("scripts/iso/build_iso.sh").read_text()
           assert "btrfs" in content.lower()

       def test_build_script_has_uefi_support(self):
           content = Path("scripts/iso/build_iso.sh").read_text()
           assert "UEFI" in content or "grub-mkrescue" in content

       def test_build_script_generates_sha256(self):
           content = Path("scripts/iso/build_iso.sh").read_text()
           assert "sha256sum" in content

       def test_build_script_cleans_temp(self):
           content = Path("scripts/iso/build_iso.sh").read_text()
           assert "rm -rf" in content
           assert "BUILD_DIR" in content

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/iso/ -v

VERIFICAR:
- [ ] scripts/iso/build_iso.sh existe y es ejecutable
- [ ] scripts/iso/verify_iso.sh existe y es ejecutable
- [ ] Build script tiene 8 pasos claros
- [ ] Verify script verifica: integridad, estructura, boot QEMU, boot UEFI
- [ ] Servicios systemd configurados (ollama, yeyo-os, guardian)
- [ ] GRUB config con normal + recovery + memtest
- [ ] SHA256 generado y verificable
- [ ] TODOS los tests pasan

SI FALLA:
- Permisos: chmod +x scripts/iso/*.sh
- QEMU: apt install qemu-system-x86

NO HACER:
- No ejecutar build_iso.sh en tests (requiere root + mucho espacio)
- No ejecutar verify_iso.sh sin una ISO real

GATE: Scripts de build y verificación de ISO completos, estructura verificable, tests de script pasan.
```
