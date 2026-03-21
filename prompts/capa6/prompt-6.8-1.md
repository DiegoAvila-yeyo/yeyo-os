## ═══════════════════════════════════════
## MICRO-FASE 6.8 — Network Firewall Advanced
## Tipo: CLI | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 6.8-1 [CLI] — Firewall avanzado con nftables

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 6.8 de Capa 6 (Sistema Inmune): implementar el firewall avanzado con nftables, extendiendoel firewall básico de Capa 0.11.

CONTEXTO:
- Micro-fases 6.0-6.7 completadas: Guardian + Anomaly + Auto-Response + Kill Switch + Snapshots + Backup + Anti-Ransomware + Honeypots
- Extiende el firewall básico de Capa 0.11
- Reglas por container, rate limiting, protección DDoS básica
- Logging de intentos bloqueados
- Whitelist-only para outgoing (configurable por nodo)
- Integra con Guardian para bloqueo dinámico de IPs

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/security/firewall.py:

   Ruta: ~/yeyo-os/src/security/firewall.py
   Contenido:

   """
   YeyoOS — Network Firewall Advanced
   Micro-fase 6.8 — Capa 6: Sistema Inmune

   Firewall avanzado con nftables.
   Per-container rules, rate limiting, DDoS protection.
   Whitelist-only para outgoing configurable por nodo.
   """

   import subprocess
   import json
   import logging
   from datetime import datetime, timezone
   from dataclasses import dataclass, field, asdict
   from typing import Optional
   from enum import Enum

   logger = logging.getLogger("yeyo.security.firewall")

   # ═══════════════════════════════════
   # TIPOS DE DATOS
   # ═══════════════════════════════════

   class FirewallAction(str, Enum):
       ACCEPT = "accept"
       DROP = "drop"
       REJECT = "reject"
       LOG = "log"

   class Protocol(str, Enum):
       TCP = "tcp"
       UDP = "udp"
       ICMP = "icmp"
       ALL = "all"

   @dataclass
   class FirewallRule:
       """Regla individual de firewall."""
       id: str
       description: str
       direction: str  # "input", "output", "forward"
       action: FirewallAction
       protocol: Protocol = Protocol.ALL
       source_ip: Optional[str] = None
       dest_ip: Optional[str] = None
       source_port: Optional[int] = None
       dest_port: Optional[int] = None
       container_id: Optional[str] = None
       rate_limit: Optional[str] = None  # e.g., "10/second"
       priority: int = 100
       enabled: bool = True
       created_at: str = ""

   @dataclass
   class BlockedAttempt:
       """Registro de intento bloqueado."""
       timestamp: str
       source_ip: str
       dest_port: int
       protocol: str
       rule_id: str
       reason: str

   @dataclass
   class FirewallConfig:
       """Configuración del firewall."""
       nft_binary: str = "nft"
       table_name: str = "yeyo_firewall"
       log_blocked: bool = True
       default_input_policy: FirewallAction = FirewallAction.DROP
       default_output_policy: FirewallAction = FirewallAction.ACCEPT
       default_forward_policy: FirewallAction = FirewallAction.DROP
       rules_file: str = "/etc/yeyo/firewall-rules.json"
       max_blocked_log: int = 10000

   # ═══════════════════════════════════
   # REGLAS POR DEFECTO
   # ═══════════════════════════════════

   DEFAULT_RULES = [
       # Permitir loopback
       FirewallRule(
           id="allow-loopback",
           description="Permitir tráfico loopback",
           direction="input",
           action=FirewallAction.ACCEPT,
           source_ip="127.0.0.0/8",
       ),
       # Permitir conexiones establecidas
       FirewallRule(
           id="allow-established",
           description="Permitir conexiones establecidas",
           direction="input",
           action=FirewallAction.ACCEPT,
       ),
       # Permitir SSH real (no honeypot)
       FirewallRule(
           id="allow-ssh",
           description="Permitir SSH (puerto 22)",
           direction="input",
           action=FirewallAction.ACCEPT,
           protocol=Protocol.TCP,
           dest_port=22,
           rate_limit="3/minute",
       ),
       # Guardian API
       FirewallRule(
           id="allow-guardian-api",
           description="Permitir Guardian API (solo local)",
           direction="input",
           action=FirewallAction.ACCEPT,
           protocol=Protocol.TCP,
           source_ip="127.0.0.1",
           dest_port=9090,
       ),
       # Rate limit para HTTP
       FirewallRule(
           id="rate-limit-http",
           description="Rate limit HTTP",
           direction="input",
           action=FirewallAction.ACCEPT,
           protocol=Protocol.TCP,
           dest_port=80,
           rate_limit="100/second",
       ),
       FirewallRule(
           id="rate-limit-https",
           description="Rate limit HTTPS",
           direction="input",
           action=FirewallAction.ACCEPT,
           protocol=Protocol.TCP,
           dest_port=443,
           rate_limit="100/second",
       ),
       # Drop ICMP flood (DDoS básico)
       FirewallRule(
           id="icmp-rate-limit",
           description="Rate limit ICMP (anti-ping flood)",
           direction="input",
           action=FirewallAction.ACCEPT,
           protocol=Protocol.ICMP,
           rate_limit="1/second",
       ),
   ]

   # ═══════════════════════════════════
   # FIREWALL MANAGER
   # ═══════════════════════════════════

   class FirewallManager:
       """Gestor de firewall avanzado con nftables."""

       def __init__(self, config: Optional[FirewallConfig] = None):
           self.config = config or FirewallConfig()
           self._rules: list[FirewallRule] = list(DEFAULT_RULES)
           self._blocked: list[BlockedAttempt] = []
           self._dynamic_blocks: dict[str, str] = {}  # ip -> reason

       # ═══════════════════════════════════
       # GESTIÓN DE REGLAS
       # ═══════════════════════════════════

       def add_rule(self, rule: FirewallRule) -> None:
           """Agrega una regla de firewall."""
           rule.created_at = datetime.now(timezone.utc).isoformat()
           self._rules.append(rule)
           logger.info(f"Regla agregada: {rule.id} — {rule.description}")

       def remove_rule(self, rule_id: str) -> bool:
           """Elimina una regla por ID."""
           original_len = len(self._rules)
           self._rules = [r for r in self._rules if r.id != rule_id]
           removed = len(self._rules) < original_len
           if removed:
               logger.info(f"Regla eliminada: {rule_id}")
           return removed

       def get_rules(self) -> list[FirewallRule]:
           """Retorna todas las reglas activas."""
           return [r for r in self._rules if r.enabled]

       # ═══════════════════════════════════
       # REGLAS POR CONTAINER
       # ═══════════════════════════════════

       def isolate_container(self, container_id: str, reason: str = "") -> None:
           """Aísla un container de la red (bloquea todo su tráfico)."""
           rule = FirewallRule(
               id=f"isolate-{container_id}",
               description=f"Aislar container {container_id}: {reason}",
               direction="forward",
               action=FirewallAction.DROP,
               container_id=container_id,
               priority=1,  # Máxima prioridad
           )
           self.add_rule(rule)
           logger.warning(f"Container aislado: {container_id} — {reason}")

       def unisolate_container(self, container_id: str) -> None:
           """Restaura la red de un container."""
           self.remove_rule(f"isolate-{container_id}")
           logger.info(f"Container des-aislado: {container_id}")

       def set_container_whitelist(
           self,
           container_id: str,
           allowed_destinations: list[str],
       ) -> None:
           """Configura whitelist de destinos para un container."""
           # Bloquear todo outgoing del container
           self.add_rule(FirewallRule(
               id=f"block-out-{container_id}",
               description=f"Bloquear outgoing de {container_id}",
               direction="output",
               action=FirewallAction.DROP,
               container_id=container_id,
               priority=50,
           ))

           # Permitir solo destinos en whitelist
           for i, dest in enumerate(allowed_destinations):
               self.add_rule(FirewallRule(
                   id=f"allow-out-{container_id}-{i}",
                   description=f"Whitelist {container_id} → {dest}",
                   direction="output",
                   action=FirewallAction.ACCEPT,
                   container_id=container_id,
                   dest_ip=dest,
                   priority=10,
               ))

       # ═══════════════════════════════════
       # BLOQUEO DINÁMICO (Guardian)
       # ═══════════════════════════════════

       def block_ip(self, ip: str, reason: str = "") -> None:
           """Bloquea una IP dinámicamente (llamado por Guardian)."""
           self._dynamic_blocks[ip] = reason
           self.add_rule(FirewallRule(
               id=f"block-ip-{ip.replace('.', '-')}",
               description=f"IP bloqueada: {ip} — {reason}",
               direction="input",
               action=FirewallAction.DROP,
               source_ip=ip,
               priority=1,
           ))
           logger.warning(f"IP bloqueada: {ip} — {reason}")

       def unblock_ip(self, ip: str) -> None:
           """Desbloquea una IP."""
           self._dynamic_blocks.pop(ip, None)
           self.remove_rule(f"block-ip-{ip.replace('.', '-')}")
           logger.info(f"IP desbloqueada: {ip}")

       def get_blocked_ips(self) -> dict[str, str]:
           """Retorna IPs bloqueadas dinámicamente."""
           return self._dynamic_blocks.copy()

       # ═══════════════════════════════════
       # LOGGING DE INTENTOS BLOQUEADOS
       # ═══════════════════════════════════

       def log_blocked(
           self,
           source_ip: str,
           dest_port: int,
           protocol: str,
           rule_id: str,
           reason: str,
       ) -> None:
           """Registra un intento bloqueado."""
           attempt = BlockedAttempt(
               timestamp=datetime.now(timezone.utc).isoformat(),
               source_ip=source_ip,
               dest_port=dest_port,
               protocol=protocol,
               rule_id=rule_id,
               reason=reason,
           )
           self._blocked.append(attempt)

           # Mantener máximo
           if len(self._blocked) > self.config.max_blocked_log:
               self._blocked = self._blocked[-self.config.max_blocked_log:]

           logger.info(
               f"Bloqueado: {source_ip}:{dest_port}/{protocol} — {reason}"
           )

       def get_blocked_attempts(self) -> list[BlockedAttempt]:
           """Retorna intentos bloqueados."""
           return self._blocked.copy()

       # ═══════════════════════════════════
       # APLICAR REGLAS CON NFTABLES
       # ═══════════════════════════════════

       def apply_rules(self) -> bool:
           """Genera y aplica las reglas nftables."""
           nft_script = self._generate_nft_script()
           logger.info("Aplicando reglas nftables...")

           try:
               result = subprocess.run(
                   [self.config.nft_binary, "-f", "-"],
                   input=nft_script,
                   capture_output=True, text=True, timeout=30,
               )

               if result.returncode == 0:
                   logger.info("Reglas nftables aplicadas correctamente")
                   return True
               else:
                   logger.error(f"Error aplicando nftables: {result.stderr}")
                   return False

           except (subprocess.SubprocessError, FileNotFoundError) as e:
               logger.error(f"Error ejecutando nft: {e}")
               return False

       def _generate_nft_script(self) -> str:
           """Genera script nftables a partir de las reglas."""
           lines = [
               f"flush table inet {self.config.table_name}",
               f"table inet {self.config.table_name} {{",
               "  chain input {",
               "    type filter hook input priority 0; policy drop;",
               "    ct state established,related accept",
           ]

           for rule in sorted(self._rules, key=lambda r: r.priority):
               if not rule.enabled or rule.direction != "input":
                   continue
               lines.append(f"    # {rule.description}")
               nft_rule = self._rule_to_nft(rule)
               if nft_rule:
                   lines.append(f"    {nft_rule}")

           lines.extend([
               "  }",
               "  chain output {",
               f"    type filter hook output priority 0; policy {self.config.default_output_policy.value};",
               "  }",
               "  chain forward {",
               f"    type filter hook forward priority 0; policy {self.config.default_forward_policy.value};",
           ])

           for rule in sorted(self._rules, key=lambda r: r.priority):
               if not rule.enabled or rule.direction != "forward":
                   continue
               lines.append(f"    # {rule.description}")
               nft_rule = self._rule_to_nft(rule)
               if nft_rule:
                   lines.append(f"    {nft_rule}")

           lines.extend([
               "  }",
               "}",
           ])

           return "\n".join(lines)

       def _rule_to_nft(self, rule: FirewallRule) -> str:
           """Convierte una regla a sintaxis nftables."""
           parts = []

           if rule.protocol != Protocol.ALL:
               parts.append(f"meta l4proto {rule.protocol.value}")

           if rule.source_ip:
               parts.append(f"ip saddr {rule.source_ip}")

           if rule.dest_ip:
               parts.append(f"ip daddr {rule.dest_ip}")

           if rule.dest_port:
               proto = rule.protocol.value if rule.protocol != Protocol.ALL else "tcp"
               parts.append(f"{proto} dport {rule.dest_port}")

           if rule.rate_limit:
               parts.append(f"limit rate {rule.rate_limit}")

           parts.append(rule.action.value)

           return " ".join(parts)

       # ═══════════════════════════════════
       # ESTADO
       # ═══════════════════════════════════

       def get_status(self) -> dict:
           """Retorna estado del firewall."""
           return {
               "total_rules": len(self._rules),
               "active_rules": len(self.get_rules()),
               "blocked_ips": len(self._dynamic_blocks),
               "blocked_attempts": len(self._blocked),
               "default_input": self.config.default_input_policy.value,
               "default_output": self.config.default_output_policy.value,
           }

2. Crear archivo tests/unit/security/test_firewall.py:

   Ruta: ~/yeyo-os/tests/unit/security/test_firewall.py
   Contenido:

   """Tests para Network Firewall Advanced — Micro-fase 6.8"""

   import pytest
   from src.security.firewall import (
       FirewallManager,
       FirewallConfig,
       FirewallRule,
       FirewallAction,
       Protocol,
       DEFAULT_RULES,
   )


   @pytest.fixture
   def manager():
       return FirewallManager()


   class TestFirewallRules:
       def test_default_rules_loaded(self, manager):
           rules = manager.get_rules()
           assert len(rules) > 0

       def test_add_rule(self, manager):
           initial = len(manager.get_rules())
           manager.add_rule(FirewallRule(
               id="test-rule",
               description="Test rule",
               direction="input",
               action=FirewallAction.DROP,
           ))
           assert len(manager.get_rules()) == initial + 1

       def test_remove_rule(self, manager):
           manager.add_rule(FirewallRule(
               id="to-remove",
               description="Will be removed",
               direction="input",
               action=FirewallAction.DROP,
           ))
           assert manager.remove_rule("to-remove") is True
           assert manager.remove_rule("nonexistent") is False


   class TestContainerIsolation:
       def test_isolate_container(self, manager):
           manager.isolate_container("abc123", "anomaly detected")
           rules = manager.get_rules()
           isolate_rules = [r for r in rules if "isolate" in r.id]
           assert len(isolate_rules) == 1

       def test_unisolate_container(self, manager):
           manager.isolate_container("abc123")
           manager.unisolate_container("abc123")
           rules = manager.get_rules()
           isolate_rules = [r for r in rules if "isolate-abc123" in r.id]
           assert len(isolate_rules) == 0

       def test_container_whitelist(self, manager):
           manager.set_container_whitelist("node-1", ["10.0.0.1", "10.0.0.2"])
           rules = manager.get_rules()
           whitelist_rules = [r for r in rules if "node-1" in r.id]
           # 1 block + 2 allow
           assert len(whitelist_rules) == 3


   class TestDynamicBlocking:
       def test_block_ip(self, manager):
           manager.block_ip("192.168.1.100", "suspicious activity")
           assert "192.168.1.100" in manager.get_blocked_ips()

       def test_unblock_ip(self, manager):
           manager.block_ip("10.0.0.1")
           manager.unblock_ip("10.0.0.1")
           assert "10.0.0.1" not in manager.get_blocked_ips()

       def test_blocked_attempts_logged(self, manager):
           manager.log_blocked("1.2.3.4", 22, "tcp", "rule-1", "brute force")
           attempts = manager.get_blocked_attempts()
           assert len(attempts) == 1
           assert attempts[0].source_ip == "1.2.3.4"


   class TestFirewallStatus:
       def test_status(self, manager):
           status = manager.get_status()
           assert status["total_rules"] > 0
           assert status["default_input"] == "drop"

       def test_rate_limit_rules_exist(self, manager):
           rules = manager.get_rules()
           rate_limited = [r for r in rules if r.rate_limit]
           assert len(rate_limited) > 0

3. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/security/test_firewall.py -v

VERIFICAR:
- [ ] Archivo src/security/firewall.py existe con FirewallManager
- [ ] Reglas por container funcionan (isolate/unisolate)
- [ ] Rate limiting configurado para SSH, HTTP, ICMP
- [ ] Bloqueo dinámico de IPs (integración Guardian)
- [ ] Intentos bloqueados se registran
- [ ] Whitelist por container funciona
- [ ] Default policy: input=DROP, output=ACCEPT
- [ ] TODOS los tests pasan

SI FALLA:
- nftables no disponible: tests verifican lógica, no ejecutan nft real
- Import error: verificar __init__.py

NO HACER:
- No ejecutar nftables en entorno de desarrollo (solo generar script)
- No abrir puertos innecesarios
- No permitir tráfico sin rate limit en producción
- No bloquear el puerto de Guardian API (9090 local)

GATE: FirewallManager gestiona reglas nftables, containers se aíslan correctamente, rate limiting funciona, bloqueo dinámico de IPs, intentos bloqueados logueados, todos los tests pasan.
```
