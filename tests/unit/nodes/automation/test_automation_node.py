"""Tests para Automation Node — Micro-fase 5.10"""

import pytest
from src.nodes.automation.service import AutomationNode


class TestAutomationCanvas:

    @pytest.mark.asyncio
    async def test_add_visual_node(self):
        node = AutomationNode()
        result = node._add_visual_node({"label": "Step 1", "type": "input"})
        assert "node_id" in result
        assert len(node._visual_nodes) == 1

    @pytest.mark.asyncio
    async def test_add_multiple_nodes(self):
        node = AutomationNode()
        node._add_visual_node({"label": "A"})
        node._add_visual_node({"label": "B"})
        node._add_visual_node({"label": "C"})
        assert len(node._visual_nodes) == 3

    @pytest.mark.asyncio
    async def test_add_visual_edge(self):
        node = AutomationNode()
        n1 = node._add_visual_node({"label": "A"})
        n2 = node._add_visual_node({"label": "B"})
        result = node._add_visual_edge({
            "source": n1["node_id"], "target": n2["node_id"]
        })
        assert "edge_id" in result
        assert len(node._visual_edges) == 1

    @pytest.mark.asyncio
    async def test_self_connection_rejected(self):
        node = AutomationNode()
        n1 = node._add_visual_node({"label": "A"})
        result = node._add_visual_edge({
            "source": n1["node_id"], "target": n1["node_id"]
        })
        assert "error" in result

    @pytest.mark.asyncio
    async def test_edge_invalid_source(self):
        node = AutomationNode()
        n1 = node._add_visual_node({"label": "A"})
        result = node._add_visual_edge({
            "source": "nonexistent", "target": n1["node_id"]
        })
        assert "error" in result

    @pytest.mark.asyncio
    async def test_remove_node_removes_edges(self):
        node = AutomationNode()
        n1 = node._add_visual_node({"label": "A"})
        n2 = node._add_visual_node({"label": "B"})
        node._add_visual_edge({"source": n1["node_id"], "target": n2["node_id"]})
        result = node._remove_visual_node(n1["node_id"])
        assert result["edges_removed"] == 1
        assert len(node._visual_edges) == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_node(self):
        node = AutomationNode()
        result = node._remove_visual_node("nonexistent")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_remove_edge(self):
        node = AutomationNode()
        n1 = node._add_visual_node({"label": "A"})
        n2 = node._add_visual_node({"label": "B"})
        edge = node._add_visual_edge({"source": n1["node_id"], "target": n2["node_id"]})
        result = node._remove_visual_edge(edge["edge_id"])
        assert "removed" in result
        assert len(node._visual_edges) == 0

    @pytest.mark.asyncio
    async def test_remove_nonexistent_edge(self):
        node = AutomationNode()
        result = node._remove_visual_edge("nonexistent")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_save_pipeline(self):
        node = AutomationNode()
        node._add_visual_node({"label": "Step 1"})
        result = node._save_pipeline("Mi Pipeline")
        assert result["saved"] == "Mi Pipeline"
        assert "Mi Pipeline" in node._saved_pipelines

    @pytest.mark.asyncio
    async def test_save_empty_name_rejected(self):
        node = AutomationNode()
        result = node._save_pipeline("")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_save_whitespace_name_rejected(self):
        node = AutomationNode()
        result = node._save_pipeline("   ")
        assert "error" in result

    @pytest.mark.asyncio
    async def test_render_ui_has_nodes_and_edges(self):
        node = AutomationNode()
        node._add_visual_node({"label": "A"})
        ui = await node.render_ui()
        assert len(ui["props"]["nodes"]) == 1
        assert ui["component"] == "AutomationNode"


class TestAutomationValidation:

    @pytest.mark.asyncio
    async def test_validate_empty_pipeline(self):
        node = AutomationNode()
        result = await node._validate_pipeline()
        assert result["valid"] is False
        assert "vacío" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_linear_pipeline(self):
        node = AutomationNode()
        n1 = node._add_visual_node({"label": "Input"})
        n2 = node._add_visual_node({"label": "Process"})
        n3 = node._add_visual_node({"label": "Output"})
        node._add_visual_edge({"source": n1["node_id"], "target": n2["node_id"]})
        node._add_visual_edge({"source": n2["node_id"], "target": n3["node_id"]})
        result = await node._validate_pipeline()
        assert result["valid"] is True
        assert result["nodes"] == 3
        assert result["edges"] == 2

    @pytest.mark.asyncio
    async def test_validate_detects_cycle(self):
        node = AutomationNode()
        n1 = node._add_visual_node({"label": "A"})
        n2 = node._add_visual_node({"label": "B"})
        n3 = node._add_visual_node({"label": "C"})
        node._add_visual_edge({"source": n1["node_id"], "target": n2["node_id"]})
        node._add_visual_edge({"source": n2["node_id"], "target": n3["node_id"]})
        node._add_visual_edge({"source": n3["node_id"], "target": n1["node_id"]})
        result = await node._validate_pipeline()
        assert result["valid"] is False
        assert "ciclos" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_single_node_valid(self):
        node = AutomationNode()
        node._add_visual_node({"label": "Solo"})
        result = await node._validate_pipeline()
        assert result["valid"] is True


class TestAutomationExecution:

    @pytest.mark.asyncio
    async def test_execute_linear_pipeline(self):
        node = AutomationNode()
        n1 = node._add_visual_node({"label": "Input"})
        n2 = node._add_visual_node({"label": "Process"})
        n3 = node._add_visual_node({"label": "Output"})
        node._add_visual_edge({"source": n1["node_id"], "target": n2["node_id"]})
        node._add_visual_edge({"source": n2["node_id"], "target": n3["node_id"]})
        result = await node._execute_pipeline()
        assert result["status"] == "completed"
        assert result["steps_executed"] == 3
        assert result["execution_order"] == ["Input", "Process", "Output"]

    @pytest.mark.asyncio
    async def test_execute_cyclic_pipeline_fails(self):
        node = AutomationNode()
        n1 = node._add_visual_node({"label": "A"})
        n2 = node._add_visual_node({"label": "B"})
        node._add_visual_edge({"source": n1["node_id"], "target": n2["node_id"]})
        node._add_visual_edge({"source": n2["node_id"], "target": n1["node_id"]})
        result = await node._execute_pipeline()
        assert "error" in result

    @pytest.mark.asyncio
    async def test_process_unknown_action(self):
        node = AutomationNode()
        result = await node.process({"action": "unknown"})
        assert "error" in result

    @pytest.mark.asyncio
    async def test_process_add_node_action(self):
        node = AutomationNode()
        result = await node.process({"action": "add_node", "label": "Test"})
        assert "node_id" in result

    @pytest.mark.asyncio
    async def test_cleanup_clears_state(self):
        node = AutomationNode()
        node._add_visual_node({"label": "A"})
        node._add_visual_node({"label": "B"})
        await node.cleanup()
        assert len(node._visual_nodes) == 0
        assert len(node._visual_edges) == 0
