"""Tests para Node Registry — Micro-fase 5.16"""

import pytest
from src.nodes.base import NodeBase, PrivilegeLevel
from src.nodes.registry import NodeRegistry, NodeNotFoundError


class FakeNode(NodeBase):
    async def initialize(self): pass
    async def render_ui(self) -> dict: return {}
    async def process(self, input_data: dict) -> dict: return {}
    async def cleanup(self): pass

    def __init__(self):
        super().__init__(name="Fake", version="1.0")


class TestNodeRegistryRegister:

    def setup_method(self):
        NodeRegistry.clear()

    def test_register_adds_node(self):
        NodeRegistry.register("fake", FakeNode)
        assert "fake" in NodeRegistry.list_types()

    def test_register_non_nodebase_raises(self):
        with pytest.raises(TypeError):
            NodeRegistry.register("bad", dict)

    def test_register_with_metadata(self):
        NodeRegistry.register("fake", FakeNode, {"icon": "🧪"})
        info = NodeRegistry.get_info("fake")
        assert info["icon"] == "🧪"


class TestNodeRegistryCreate:

    def setup_method(self):
        NodeRegistry.clear()

    def test_create_returns_instance(self):
        NodeRegistry.register("fake", FakeNode)
        node = NodeRegistry.create("fake")
        assert isinstance(node, FakeNode)
        assert isinstance(node, NodeBase)

    def test_create_unknown_raises(self):
        with pytest.raises(NodeNotFoundError):
            NodeRegistry.create("nonexistent")


class TestNodeRegistryList:

    def setup_method(self):
        NodeRegistry.clear()

    def test_list_types(self):
        NodeRegistry.register("a", FakeNode)
        NodeRegistry.register("b", FakeNode)
        types = NodeRegistry.list_types()
        assert "a" in types
        assert "b" in types

    def test_is_registered(self):
        NodeRegistry.register("fake", FakeNode)
        assert NodeRegistry.is_registered("fake") is True
        assert NodeRegistry.is_registered("nope") is False

    def test_get_info(self):
        NodeRegistry.register("fake", FakeNode)
        info = NodeRegistry.get_info("fake")
        assert info["type"] == "fake"
        assert info["class_name"] == "FakeNode"

    def test_get_info_unknown_raises(self):
        with pytest.raises(NodeNotFoundError):
            NodeRegistry.get_info("nonexistent")


class TestNodeRegistryUnregister:

    def setup_method(self):
        NodeRegistry.clear()

    def test_unregister(self):
        NodeRegistry.register("fake", FakeNode)
        assert NodeRegistry.unregister("fake") is True
        assert "fake" not in NodeRegistry.list_types()

    def test_unregister_unknown_returns_false(self):
        assert NodeRegistry.unregister("nonexistent") is False

    def test_clear(self):
        NodeRegistry.register("a", FakeNode)
        NodeRegistry.register("b", FakeNode)
        NodeRegistry.clear()
        assert len(NodeRegistry.list_types()) == 0
