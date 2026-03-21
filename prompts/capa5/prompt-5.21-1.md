## ═══════════════════════════════════════
## MICRO-FASE 5.21 — Integration Test Capa 5
## Tipo: MIXTA | Prompts: 1 | Complejidad: Compleja
## ═══════════════════════════════════════

### PROMPT 5.21-1 [MIXTA] — Test de integración completo de Capa 5

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.21 de Capa 5 (Órganos): test de integración completo de toda la Capa 5 y regresión de Capas 0-4.

CONTEXTO:
- Capa 5 COMPLETA: 22 micro-fases, todos los nodos, registry, API, MiniChat v1-v3, health monitor
- Este test verifica que TODO funciona junto:
  - Cada tipo de nodo se puede abrir y cerrar
  - Containers aislados correctamente
  - GPU scheduling funciona entre nodos
  - MiniChat funciona en contexto de cada nodo
  - MiniChat v3 detecta y ejecuta acciones
  - Health monitor detecta crasheos y reinicia
  - Capas 0-4 no se rompieron (regresión)
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

PARTE 1 — VS CODE: Crear tests de integración

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear estructura:
   mkdir -p tests/integration

2. Crear archivo tests/integration/__init__.py (vacío):

   Ruta: ~/yeyo-os/tests/integration/__init__.py
   Contenido: (archivo vacío)

3. Crear archivo tests/integration/test_capa5_integration.py:

   Ruta: ~/yeyo-os/tests/integration/test_capa5_integration.py
   Contenido:

   """
   Tests de Integración — Capa 5: Órganos
   Micro-fase 5.21

   Test completo de todos los nodos, registry, API, MiniChat, health monitor.
   Incluye regresión de Capas 0-4.
   """

   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock

   from src.nodes.base import NodeBase, NodeStatus, PrivilegeLevel
   from src.nodes.registry import NodeRegistry, NodeNotFoundError
   from src.nodes.health_monitor import NodeHealthMonitor, MAX_RESTART_ATTEMPTS


   # ═══════════════════════════════════
   # SECTION 1: NodeBase Contract
   # ═══════════════════════════════════

   class TestNodeBaseContract:
       """Todos los nodos deben cumplir el contrato de NodeBase."""

       def test_nodebase_is_abstract(self):
           with pytest.raises(TypeError):
               NodeBase(name="test", version="1.0")

       def test_abstract_methods_count(self):
           assert len(NodeBase.__abstractmethods__) == 4

       def test_abstract_methods_names(self):
           expected = {"initialize", "render_ui", "process", "cleanup"}
           assert NodeBase.__abstractmethods__ == expected


   # ═══════════════════════════════════
   # SECTION 2: Node Registry
   # ═══════════════════════════════════

   class ConcreteNode(NodeBase):
       async def initialize(self): pass
       async def render_ui(self) -> dict: return {"component": "Test"}
       async def process(self, input_data: dict) -> dict: return input_data
       async def cleanup(self): pass
       def __init__(self): super().__init__(name="Concrete", version="1.0")

   class TestNodeRegistryIntegration:

       def setup_method(self):
           NodeRegistry.clear()

       def test_register_and_create(self):
           NodeRegistry.register("concrete", ConcreteNode)
           node = NodeRegistry.create("concrete")
           assert isinstance(node, ConcreteNode)
           assert isinstance(node, NodeBase)

       def test_create_unknown_raises(self):
           with pytest.raises(NodeNotFoundError):
               NodeRegistry.create("nonexistent")

       def test_list_types_after_register(self):
           NodeRegistry.register("a", ConcreteNode)
           NodeRegistry.register("b", ConcreteNode)
           types = NodeRegistry.list_types()
           assert len(types) == 2
           assert "a" in types
           assert "b" in types


   # ═══════════════════════════════════
   # SECTION 3: Node Lifecycle
   # ═══════════════════════════════════

   class TestNodeLifecycleIntegration:

       @pytest.mark.asyncio
       async def test_full_lifecycle(self):
           node = ConcreteNode()
           assert node.status == NodeStatus.CREATED

           await node.open()
           assert node.status == NodeStatus.READY

           result = await node.process({"test": True})
           assert result["test"] is True

           ui = await node.render_ui()
           assert "component" in ui

           await node.close()
           assert node.status == NodeStatus.CLOSED

       @pytest.mark.asyncio
       async def test_status_reporting(self):
           node = ConcreteNode()
           status = await node.get_status()
           assert status["name"] == "Concrete"
           assert status["gpu_allocated"] is False


   # ═══════════════════════════════════
   # SECTION 4: GPU Scheduling (Mock)
   # ═══════════════════════════════════

   class TestGPUSchedulingIntegration:

       @pytest.mark.asyncio
       async def test_gpu_request_and_release(self):
           node = ConcreteNode()
           mock_scheduler = MagicMock()
           mock_scheduler.allocate = AsyncMock(return_value=True)
           mock_scheduler.release = AsyncMock()
           mock_scheduler.get_instance = MagicMock(return_value=mock_scheduler)

           with patch("src.nodes.base.GPUScheduler", mock_scheduler):
               result = await node.request_gpu(vram_mb=2048, priority=1)
               assert result is True
               assert node._gpu_allocated is True

               await node.release_gpu()
               assert node._gpu_allocated is False

       @pytest.mark.asyncio
       async def test_mining_node_gpu_blocked(self):
           """Mining Node NUNCA puede usar GPU."""
           from src.nodes.mining.service import MiningNode
           mining = MiningNode()
           result = await mining.request_gpu(vram_mb=1024)
           assert result is False


   # ═══════════════════════════════════
   # SECTION 5: MiniChat Context
   # ═══════════════════════════════════

   class TestMiniChatContextIntegration:

       def test_context_changes_per_node_type(self):
           from src.minichat.service import MiniChatV2Service
           service = MiniChatV2Service()

           service.set_context("image", "node-1")
           image_suggestions = service.get_suggestions()

           service.set_context("code", "node-2")
           code_suggestions = service.get_suggestions()

           assert image_suggestions != code_suggestions


   # ═══════════════════════════════════
   # SECTION 6: MiniChat Actions
   # ═══════════════════════════════════

   class TestMiniChatActionsIntegration:

       def test_action_detection_per_node(self):
           from src.minichat.actions import ActionDetector, ActionType
           detector = ActionDetector()

           img_action = detector.detect("genera una imagen de un gato", "image")
           assert img_action.action_type == ActionType.GENERATE_IMAGE

           code_action = detector.detect("ejecuta este código", "code")
           assert code_action.action_type == ActionType.EXECUTE_CODE

           video_action = detector.detect("recorta del minuto 2 al 5", "video")
           assert video_action.action_type == ActionType.TRIM_VIDEO

           normal = detector.detect("hola mundo", "image")
           assert normal.action_type == ActionType.NONE

       def test_actions_require_confirmation(self):
           from src.minichat.actions import ActionDetector
           detector = ActionDetector()

           action = detector.detect("genera una imagen", "image")
           assert action.requires_confirmation is True


   # ═══════════════════════════════════
   # SECTION 7: Health Monitor
   # ═══════════════════════════════════

   class TestHealthMonitorIntegration:

       @pytest.mark.asyncio
       async def test_monitor_healthy_nodes(self):
           monitor = NodeHealthMonitor()
           node1 = ConcreteNode()
           node1.status = NodeStatus.READY
           node2 = ConcreteNode()
           node2.status = NodeStatus.READY

           results = await monitor.check_all({node1.id: node1, node2.id: node2})
           assert len(results) == 2
           assert all(r.is_healthy for r in results)

       @pytest.mark.asyncio
       async def test_monitor_detects_crash_and_restarts(self):
           monitor = NodeHealthMonitor()
           node = ConcreteNode()
           node.status = NodeStatus.ERROR
           node.close = AsyncMock()
           node.open = AsyncMock(side_effect=lambda: setattr(node, 'status', NodeStatus.READY))

           result = await monitor.check_node(node)
           assert result.restart_count >= 1

       def test_max_restart_is_three(self):
           assert MAX_RESTART_ATTEMPTS == 3

       @pytest.mark.asyncio
       async def test_health_report(self):
           monitor = NodeHealthMonitor()
           node = ConcreteNode()
           node.status = NodeStatus.READY
           await monitor.check_node(node)

           report = monitor.get_health_report()
           assert report["total_nodes"] == 1
           assert report["healthy"] == 1


   # ═══════════════════════════════════
   # SECTION 8: Security Checks
   # ═══════════════════════════════════

   class TestSecurityIntegration:

       def test_sandbox_code_timeout(self):
           from src.nodes.code.sandbox import SANDBOX_TIMEOUT
           assert SANDBOX_TIMEOUT == 30

       def test_sandbox_memory_limit(self):
           from src.nodes.code.sandbox import SANDBOX_MEMORY
           assert SANDBOX_MEMORY == "256m"

       def test_ffmpeg_validation_blocks_dangerous(self):
           from src.nodes.video.ffmpeg_validator import FFmpegValidator
           validator = FFmpegValidator()

           result = validator.validate("ffmpeg -y -i input.mp4 output.mp4")
           assert result.is_valid is False

           result = validator.validate("ffmpeg -i input.mp4 output.mp4; rm -rf /")
           assert result.is_valid is False

       def test_ffmpeg_validation_allows_safe(self):
           from src.nodes.video.ffmpeg_validator import FFmpegValidator
           validator = FFmpegValidator()

           result = validator.validate("ffmpeg -i input.mp4 -ss 00:02:00 -c copy output.mp4")
           assert result.is_valid is True

       def test_mining_node_gpu_flag(self):
           from src.nodes.mining.service import MiningNode
           assert MiningNode.GPU_MINING_BLOCKED is True

4. Ejecutar tests de integración:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/integration/test_capa5_integration.py -v

PARTE 2 — TERMINAL: Verificar regresión de Capas 0-4

5. Ejecutar TODOS los tests (Capas 1-5):
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/ -v --tb=short 2>&1 | tail -50

6. Verificar estructura de archivos:
   find src/nodes -name "*.py" | sort
   find frontend/src/components/nodes -name "*.tsx" | sort

VERIFICAR:
- [ ] NodeBase es abstracta con 4 métodos
- [ ] NodeRegistry registra, crea y lista nodos
- [ ] Lifecycle completo: open → process → render_ui → close
- [ ] GPU scheduling funciona (con mocks)
- [ ] Mining Node GPU SIEMPRE bloqueado
- [ ] MiniChat v2 cambia contexto por nodo
- [ ] MiniChat v3 detecta acciones y requiere confirmación
- [ ] Health Monitor detecta crasheos y reinicia (máx 3)
- [ ] Sandbox: timeout 30s, 256MB RAM
- [ ] FFmpeg: comandos peligrosos bloqueados, seguros permitidos
- [ ] Regresión: tests de Capas 1-4 siguen pasando
- [ ] TODOS los tests pasan (unitarios + integración)

SI FALLA:
- Import errors: verificar todas las __init__.py
- Circular imports: verificar lazy imports en register_all_defaults
- Tests de capas anteriores: no modificar nada de Capas 0-4
- AsyncMock: `pip install pytest-asyncio`

NO HACER:
- No modificar código de Capas 0-4
- No relajar ninguna regla de seguridad
- No saltear tests que fallan

GATE FINAL DE CAPA 5:
✅ NodeBase abstracta con lifecycle
✅ 9 nodos funcionales: Chat, Image, Video, Code, Automation, Files, Browser, Config, Mining
✅ NodeRegistry con factory pattern
✅ REST API completa para gestión de nodos
✅ MiniChat v1→v2→v3 (básico→contexto→acciones)
✅ Health Monitor con auto-restart
✅ GPU NUNCA para minería
✅ FFmpeg SIEMPRE validado
✅ Sandbox: sin red, 30s timeout, 256MB RAM, auto-destruido
✅ Todos los tests pasan (unitarios + integración + regresión Capas 0-4)
✅ CAPA 5 COMPLETA — Los órganos de YeyoOS están vivos 🫀
```
