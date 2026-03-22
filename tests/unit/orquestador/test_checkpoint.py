"""Tests para GrafoCheckpoint — Micro-fase 5.22"""

import json
import pytest
from unittest.mock import AsyncMock, MagicMock
from src.orquestador.estado import EstadoGrafo
from src.orquestador.nodo import nodo
from src.orquestador.grafo import YeyoGrafo
from src.orquestador.checkpoint import GrafoCheckpoint, TIPO_CHECKPOINT


# ─── Mock de FlashMemory ───────────────────────────────────────────────────

def mock_flash_memory(checkpoints=None):
    m = AsyncMock()
    memoria_guardada = {}
    contador = [0]

    async def guardar(dato, metadata=None):
        contador[0] += 1
        mid = f"mem-{contador[0]:03d}"
        memoria_guardada[mid] = {"contenido": dato, "metadata": metadata}
        return mid

    async def buscar(query, tipo=None, limite=10):
        if checkpoints is not None:
            return checkpoints
        results = []
        for mid, data in memoria_guardada.items():
            if tipo is None or data.get("metadata", {}).get("tipo") == tipo:
                results.append({"id": mid, "contenido": data["contenido"], "score": 0.9})
        return results[:limite]

    m.guardar = AsyncMock(side_effect=guardar)
    m.buscar = AsyncMock(side_effect=buscar)
    m._memoria_guardada = memoria_guardada
    return m


# ─── Nodos de prueba ──────────────────────────────────────────────────────

@nodo(id="checkpoint_nodo_a")
async def checkpoint_nodo_a(estado: EstadoGrafo) -> EstadoGrafo:
    estado.salida["a"] = True
    return estado


@nodo(id="checkpoint_nodo_b")
async def checkpoint_nodo_b(estado: EstadoGrafo) -> EstadoGrafo:
    estado.salida["b"] = True
    return estado


class TestGrafoCheckpointGuardar:

    @pytest.mark.asyncio
    async def test_guardar_estado_retorna_memoria_id(self):
        flash = mock_flash_memory()
        cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
        estado = EstadoGrafo(entrada={"test": True})
        estado.registrar_nodo_completado("nodo_a")
        memoria_id = await cp.guardar_estado(estado)
        assert memoria_id != ""
        assert memoria_id.startswith("mem-")

    @pytest.mark.asyncio
    async def test_guardar_estado_llama_a_flash_memory(self):
        flash = mock_flash_memory()
        cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
        estado = EstadoGrafo(entrada={"x": 1})
        await cp.guardar_estado(estado)
        flash.guardar.assert_called_once()

    @pytest.mark.asyncio
    async def test_guardar_estado_usa_tipo_checkpoint(self):
        flash = mock_flash_memory()
        cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
        estado = EstadoGrafo(entrada={})
        await cp.guardar_estado(estado)
        metadata_usada = flash.guardar.call_args.kwargs.get("metadata", {})
        assert metadata_usada.get("tipo") == TIPO_CHECKPOINT

    @pytest.mark.asyncio
    async def test_checkpoint_registrado_en_lista(self):
        flash = mock_flash_memory()
        cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
        estado = EstadoGrafo(entrada={})
        await cp.guardar_estado(estado)
        assert len(cp.checkpoints_guardados) == 1

    @pytest.mark.asyncio
    async def test_error_en_flash_memory_no_interrumpe(self):
        flash = AsyncMock()
        flash.guardar = AsyncMock(side_effect=ConnectionError("flash down"))
        cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
        estado = EstadoGrafo(entrada={})
        resultado = await cp.guardar_estado(estado)
        assert resultado == ""

    @pytest.mark.asyncio
    async def test_on_evento_checkpoint_guarda_en_completado(self):
        flash = mock_flash_memory()
        cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
        evento = {
            "type": "graph_event",
            "grafo_id": "mi_grafo",
            "nodo_id": "nodo_a",
            "estado": "completado",
            "progreso": 0.5,
            "mensaje": "ok",
            "timestamp": "2025-01-01T00:00:00Z"
        }
        await cp.on_evento_checkpoint(evento)
        flash.guardar.assert_called_once()

    @pytest.mark.asyncio
    async def test_on_evento_checkpoint_no_guarda_en_activo(self):
        flash = mock_flash_memory()
        cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
        evento = {"estado": "activo", "nodo_id": "n", "progreso": 0.3}
        await cp.on_evento_checkpoint(evento)
        flash.guardar.assert_not_called()

    @pytest.mark.asyncio
    async def test_on_evento_checkpoint_guarda_en_saltado(self):
        flash = mock_flash_memory()
        cp = GrafoCheckpoint(flash, grafo_id="mi_grafo")
        evento = {"estado": "saltado", "nodo_id": "n", "progreso": 0.5}
        await cp.on_evento_checkpoint(evento)
        flash.guardar.assert_called_once()


class TestGrafoCheckpointReanudar:

    @pytest.mark.asyncio
    async def test_reanudar_retorna_none_si_no_hay_checkpoints(self):
        flash = mock_flash_memory(checkpoints=[])
        resultado = await GrafoCheckpoint.reanudar("mi_grafo", flash)
        assert resultado is None

    @pytest.mark.asyncio
    async def test_reanudar_reconstruye_estado(self):
        estado_original = EstadoGrafo(entrada={"x": 42})
        estado_original.registrar_nodo_completado("nodo_a")
        estado_original.salida["resultado"] = "ok"

        checkpoint_data = {
            "grafo_id": "mi_grafo",
            "estado": estado_original.a_dict(),
            "timestamp": "2025-01-01T00:00:00Z",
            "tipo": TIPO_CHECKPOINT,
        }
        flash = mock_flash_memory(checkpoints=[{
            "id": "mem-001",
            "contenido": json.dumps(checkpoint_data),
            "score": 0.9
        }])

        estado_recuperado = await GrafoCheckpoint.reanudar("mi_grafo", flash)
        assert estado_recuperado is not None
        assert estado_recuperado.entrada == {"x": 42}
        assert "nodo_a" in estado_recuperado.historial
        assert estado_recuperado.salida["resultado"] == "ok"

    @pytest.mark.asyncio
    async def test_reanudar_ignora_checkpoints_de_otro_grafo(self):
        checkpoint_data = {
            "grafo_id": "otro_grafo",
            "estado": EstadoGrafo(entrada={}).a_dict(),
            "tipo": TIPO_CHECKPOINT,
        }
        flash = mock_flash_memory(checkpoints=[{
            "id": "mem-001",
            "contenido": json.dumps(checkpoint_data),
            "score": 0.9
        }])
        resultado = await GrafoCheckpoint.reanudar("mi_grafo", flash)
        assert resultado is None

    @pytest.mark.asyncio
    async def test_reanudar_error_en_flash_retorna_none(self):
        flash = AsyncMock()
        flash.buscar = AsyncMock(side_effect=ConnectionError("flash down"))
        resultado = await GrafoCheckpoint.reanudar("mi_grafo", flash)
        assert resultado is None


class TestGrafoCheckpointIntegracion:

    @pytest.mark.asyncio
    async def test_checkpoint_integrado_con_yeyo_grafo(self):
        """GrafoCheckpoint como callback de YeyoGrafo guarda checkpoints por nodo."""
        flash = mock_flash_memory()
        cp = GrafoCheckpoint(flash, grafo_id="grafo_integ")

        g = (YeyoGrafo("grafo_integ")
             .agregar_nodo(checkpoint_nodo_a)
             .agregar_nodo(checkpoint_nodo_b)
             .inicio("checkpoint_nodo_a")
             .edge("checkpoint_nodo_a", "checkpoint_nodo_b")
             .fin("checkpoint_nodo_b"))

        await g.ejecutar({}, on_evento=cp.on_evento_checkpoint)

        assert flash.guardar.call_count >= 2
