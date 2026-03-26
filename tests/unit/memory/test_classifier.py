"""
Tests unitarios para NamespaceClassifier.
Usan mocks — no requieren Ollama corriendo.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from src.memory.classifier import NamespaceClassifier, VALID_NAMESPACES, DEFAULT_NAMESPACE
from src.ia.interfaces import IAResponse


def make_classifier(response_text: str) -> NamespaceClassifier:
    """Helper: crea clasificador con IA mockeada que responde response_text."""
    mock_ia = MagicMock()
    mock_ia.chat = AsyncMock(return_value=IAResponse(
        content=response_text,
        model="mock",
        tokens_used=5,
        latency_ms=10.0,
    ))
    return NamespaceClassifier(ia_provider=mock_ia)


class TestNamespaceClassifierBasic:
    """Tests básicos de clasificación."""

    @pytest.mark.asyncio
    async def test_classify_codigo_usuario(self):
        clf = make_classifier("codigo:usuario")
        result = await clf.classify("Prefiero TypeScript con tipos estrictos")
        assert result == "codigo:usuario"

    @pytest.mark.asyncio
    async def test_classify_chat_usuario(self):
        clf = make_classifier("chat:usuario")
        result = await clf.classify("Mi nombre es Diego y tengo 28 años")
        assert result == "chat:usuario"

    @pytest.mark.asyncio
    async def test_classify_imagen_conocimiento(self):
        clf = make_classifier("imagen:conocimiento")
        result = await clf.classify("La regla de tercios divide la imagen en 9 partes")
        assert result == "imagen:conocimiento"

    @pytest.mark.asyncio
    async def test_classify_descartado_saludo(self):
        clf = make_classifier("descartado")
        result = await clf.classify("Hola como estás")
        assert result == "descartado"

    @pytest.mark.asyncio
    async def test_classify_imagen_usuario(self):
        clf = make_classifier("imagen:usuario")
        result = await clf.classify("Me gustan las imágenes estilo anime con colores vibrantes")
        assert result == "imagen:usuario"

    @pytest.mark.asyncio
    async def test_classify_automatizacion_conocimiento(self):
        clf = make_classifier("automatizacion:conocimiento")
        result = await clf.classify("El patrón retry con exponential backoff para APIs")
        assert result == "automatizacion:conocimiento"


class TestNamespaceClassifierEdgeCases:
    """Tests de casos límite y degradación graceful."""

    @pytest.mark.asyncio
    async def test_empty_content_returns_descartado(self):
        clf = make_classifier("chat:usuario")
        result = await clf.classify("")
        assert result == "descartado"

    @pytest.mark.asyncio
    async def test_whitespace_only_returns_descartado(self):
        clf = make_classifier("chat:usuario")
        result = await clf.classify("   ")
        assert result == "descartado"

    @pytest.mark.asyncio
    async def test_short_message_returns_descartado(self):
        clf = make_classifier("chat:usuario")
        result = await clf.classify("ok")
        assert result == "descartado"

    @pytest.mark.asyncio
    async def test_two_words_returns_descartado(self):
        clf = make_classifier("chat:usuario")
        result = await clf.classify("gracias amigo")
        assert result == "descartado"

    @pytest.mark.asyncio
    async def test_invalid_namespace_returns_default(self):
        clf = make_classifier("namespace_invalido_xyz")
        result = await clf.classify("Contenido válido que debería clasificarse bien")
        assert result == DEFAULT_NAMESPACE

    @pytest.mark.asyncio
    async def test_ia_failure_returns_default(self):
        """Si la IA falla, retorna default sin crash."""
        mock_ia = MagicMock()
        mock_ia.chat = AsyncMock(side_effect=Exception("Ollama down"))
        clf = NamespaceClassifier(ia_provider=mock_ia)
        result = await clf.classify("Mensaje con contenido real y múltiples palabras")
        assert result == DEFAULT_NAMESPACE

    @pytest.mark.asyncio
    async def test_namespace_with_quotes_is_cleaned(self):
        clf = make_classifier('"codigo:usuario"')
        result = await clf.classify("Prefiero Python para scripts de automatización")
        assert result == "codigo:usuario"


class TestNamespaceClassifierBatch:
    """Tests de clasificación en batch."""

    @pytest.mark.asyncio
    async def test_classify_batch_returns_list(self):
        mock_ia = MagicMock()
        mock_ia.chat = AsyncMock(side_effect=[
            IAResponse(content="chat:usuario", model="mock", tokens_used=5, latency_ms=10.0),
            IAResponse(content="codigo:usuario", model="mock", tokens_used=5, latency_ms=10.0),
            IAResponse(content="imagen:conocimiento", model="mock", tokens_used=5, latency_ms=10.0),
        ])
        clf = NamespaceClassifier(ia_provider=mock_ia)
        results = await clf.classify_batch([
            "Mi nombre es Diego",
            "Prefiero TypeScript estricto",
            "Técnica de bokeh en fotografía",
        ])
        assert results == ["chat:usuario", "codigo:usuario", "imagen:conocimiento"]

    @pytest.mark.asyncio
    async def test_classify_batch_empty_list(self):
        clf = make_classifier("chat:usuario")
        results = await clf.classify_batch([])
        assert results == []


class TestValidNamespaces:
    """Tests que verifican el set de namespaces válidos."""

    def test_all_node_namespaces_present(self):
        expected = {
            "chat:usuario",
            "imagen:usuario", "imagen:conocimiento",
            "codigo:usuario", "codigo:conocimiento",
            "video:usuario", "video:conocimiento",
            "automatizacion:usuario", "automatizacion:conocimiento",
            "descartado",
        }
        assert expected.issubset(VALID_NAMESPACES)

    def test_default_namespace_is_valid(self):
        assert DEFAULT_NAMESPACE in VALID_NAMESPACES
