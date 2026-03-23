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
    id: str
    description: str
    direction: str
    action: FirewallAction
    protocol: Protocol = Protocol.ALL
    source_ip: Optional[str] = None
    dest_ip: Optional[str] = None
    source_port: Optional[int] = None
    dest_port: Optional[int] = None
    container_id: Optional[str] = None
    rate_limit: Optional[str] = None
    priority: int = 100
    enabled: bool = True
    created_at: str = ""


@dataclass
class BlockedAttempt:
    timestamp: str
    source_ip: str
    dest_port: int
    protocol: str
    rule_id: str
    reason: str


@dataclass
class FirewallConfig:
    nft_binary: str = "nft"
    table_name: str = "yeyo_firewall"
    log_blocked: bool = True
    default_input_policy: FirewallAction = FirewallAction.DROP
    default_output_policy: FirewallAction = FirewallAction.ACCEPT
    default_forward_policy: FirewallAction = FirewallAction.DROP
    rules_file: str = "/etc/yeyo/firewall-rules.json"
    max_blocked_log: int = 10000


DEFAULT_RULES = [
    FirewallRule(id="allow-loopback", description="Permitir trafico loopback", direction="input", action=FirewallAction.ACCEPT, source_ip="127.0.0.0/8"),
    FirewallRule(id="allow-established", description="Permitir conexiones establecidas", direction="input", action=FirewallAction.ACCEPT),
    FirewallRule(id="allow-ssh", description="Permitir SSH (puerto 22)", direction="input", action=FirewallAction.ACCEPT, protocol=Protocol.TCP, dest_port=22, rate_limit="3/minute"),
    FirewallRule(id="allow-guardian-api", description="Permitir Guardian API (solo local)", direction="input", action=FirewallAction.ACCEPT, protocol=Protocol.TCP, source_ip="127.0.0.1", dest_port=9090),
    FirewallRule(id="rate-limit-http", description="Rate limit HTTP", direction="input", action=FirewallAction.ACCEPT, protocol=Protocol.TCP, dest_port=80, rate_limit="100/second"),
    FirewallRule(id="rate-limit-https", description="Rate limit HTTPS", direction="input", action=FirewallAction.ACCEPT, protocol=Protocol.TCP, dest_port=443, rate_limit="100/second"),
    FirewallRule(id="icmp-rate-limit", description="Rate limit ICMP (anti-ping flood)", direction="input", action=FirewallAction.ACCEPT, protocol=Protocol.ICMP, rate_limit="1/second"),
]


class FirewallManager:
    def __init__(self, config: Optional[FirewallConfig] = None):
        self.config = config or FirewallConfig()
        self._rules: list[FirewallRule] = list(DEFAULT_RULES)
        self._blocked: list[BlockedAttempt] = []
        self._dynamic_blocks: dict[str, str] = {}

    def add_rule(self, rule: FirewallRule) -> None:
        rule.created_at = datetime.now(timezone.utc).isoformat()
        self._rules.append(rule)
        logger.info(f"Regla agregada: {rule.id} -- {rule.description}")

    def remove_rule(self, rule_id: str) -> bool:
        original_len = len(self._rules)
        self._rules = [r for r in self._rules if r.id != rule_id]
        removed = len(self._rules) < original_len
        if removed:
            logger.info(f"Regla eliminada: {rule_id}")
        return removed

    def get_rules(self) -> list[FirewallRule]:
        return [r for r in self._rules if r.enabled]

    def isolate_container(self, container_id: str, reason: str = "") -> None:
        rule = FirewallRule(
            id=f"isolate-{container_id}",
            description=f"Aislar container {container_id}: {reason}",
            direction="forward",
            action=FirewallAction.DROP,
            container_id=container_id,
            priority=1,
        )
        self.add_rule(rule)
        logger.warning(f"Container aislado: {container_id} -- {reason}")

    def unisolate_container(self, container_id: str) -> None:
        self.remove_rule(f"isolate-{container_id}")
        logger.info(f"Container des-aislado: {container_id}")

    def set_container_whitelist(self, container_id: str, allowed_destinations: list[str]) -> None:
        self.add_rule(FirewallRule(
            id=f"block-out-{container_id}",
            description=f"Bloquear outgoing de {container_id}",
            direction="output",
            action=FirewallAction.DROP,
            container_id=container_id,
            priority=50,
        ))
        for i, dest in enumerate(allowed_destinations):
            self.add_rule(FirewallRule(
                id=f"allow-out-{container_id}-{i}",
                description=f"Whitelist {container_id} -> {dest}",
                direction="output",
                action=FirewallAction.ACCEPT,
                container_id=container_id,
                dest_ip=dest,
                priority=10,
            ))

    def block_ip(self, ip: str, reason: str = "") -> None:
        self._dynamic_blocks[ip] = reason
        self.add_rule(FirewallRule(
            id=f"block-ip-{ip.replace('.', '-')}",
            description=f"IP bloqueada: {ip} -- {reason}",
            direction="input",
            action=FirewallAction.DROP,
            source_ip=ip,
            priority=1,
        ))
        logger.warning(f"IP bloqueada: {ip} -- {reason}")

    def unblock_ip(self, ip: str) -> None:
        self._dynamic_blocks.pop(ip, None)
        self.remove_rule(f"block-ip-{ip.replace('.', '-')}")
        logger.info(f"IP desbloqueada: {ip}")

    def get_blocked_ips(self) -> dict[str, str]:
        return self._dynamic_blocks.copy()

    def log_blocked(self, source_ip: str, dest_port: int, protocol: str, rule_id: str, reason: str) -> None:
        attempt = BlockedAttempt(
            timestamp=datetime.now(timezone.utc).isoformat(),
            source_ip=source_ip,
            dest_port=dest_port,
            protocol=protocol,
            rule_id=rule_id,
            reason=reason,
        )
        self._blocked.append(attempt)
        if len(self._blocked) > self.config.max_blocked_log:
            self._blocked = self._blocked[-self.config.max_blocked_log:]
        logger.info(f"Bloqueado: {source_ip}:{dest_port}/{protocol} -- {reason}")

    def get_blocked_attempts(self) -> list[BlockedAttempt]:
        return self._blocked.copy()

    def apply_rules(self) -> bool:
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
        lines.extend(["  }", "}"])
        return "\n".join(lines)

    def _rule_to_nft(self, rule: FirewallRule) -> str:
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

    def get_status(self) -> dict:
        return {
            "total_rules": len(self._rules),
            "active_rules": len(self.get_rules()),
            "blocked_ips": len(self._dynamic_blocks),
            "blocked_attempts": len(self._blocked),
            "default_input": self.config.default_input_policy.value,
            "default_output": self.config.default_output_policy.value,
        }
