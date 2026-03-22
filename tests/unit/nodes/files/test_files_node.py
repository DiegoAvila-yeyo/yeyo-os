"""Tests para Files Node — Micro-fase 5.12"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock
from src.nodes.files.service import FilesNode


class TestFilesNodeTree:

    def test_get_tree(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "file.txt").write_text("hello")
            Path(tmpdir, "subdir").mkdir()
            Path(tmpdir, "subdir", "inner.py").write_text("x=1")

            node = FilesNode(root_path=tmpdir)
            tree = node._get_tree(Path(tmpdir), depth=2)
            names = [item["name"] for item in tree]
            assert "file.txt" in names
            assert "subdir" in names

    def test_hidden_files_excluded(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, ".hidden").write_text("secret")
            Path(tmpdir, "visible.txt").write_text("hello")

            node = FilesNode(root_path=tmpdir)
            tree = node._get_tree(Path(tmpdir))
            names = [item["name"] for item in tree]
            assert ".hidden" not in names
            assert "visible.txt" in names

    def test_tree_depth_limit(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a").mkdir()
            Path(tmpdir, "a", "b").mkdir()
            Path(tmpdir, "a", "b", "deep.txt").write_text("deep")

            node = FilesNode(root_path=tmpdir)
            tree = node._get_tree(Path(tmpdir), depth=1)
            a_dir = [i for i in tree if i["name"] == "a"][0]
            assert a_dir["children"] == []  # depth=1 doesn't recurse


class TestFilesNodeOperations:

    def test_copy_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir, "original.txt")
            src.write_text("content")
            dst = Path(tmpdir, "copy.txt")

            node = FilesNode(root_path=tmpdir)
            result = node._copy_file(str(src), str(dst))
            assert "copied" in result
            assert dst.exists()

    def test_move_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            src = Path(tmpdir, "to_move.txt")
            src.write_text("content")
            dst = Path(tmpdir, "moved.txt")

            node = FilesNode(root_path=tmpdir)
            result = node._move_file(str(src), str(dst))
            assert "moved" in result
            assert not src.exists()
            assert dst.exists()

    def test_delete_requires_confirmation(self):
        node = FilesNode()
        result = node._delete_file("/some/path", confirmed=False)
        assert result["requires_confirmation"] is True

    def test_delete_with_confirmation(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir, "to_delete.txt")
            f.write_text("bye")

            node = FilesNode(root_path=tmpdir)
            result = node._delete_file(str(f), confirmed=True)
            assert "deleted" in result
            assert not f.exists()

    def test_list_directory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "a.txt").write_text("a")
            Path(tmpdir, "b.txt").write_text("b")

            node = FilesNode(root_path=tmpdir)
            result = node._list_directory(tmpdir)
            assert result["count"] == 2

    def test_list_nonexistent_directory(self):
        node = FilesNode()
        result = node._list_directory("/nonexistent/path")
        assert "error" in result


class TestFilesNodePreview:

    @pytest.mark.asyncio
    async def test_preview_text_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir, "test.txt")
            f.write_text("Hello World")

            node = FilesNode(root_path=tmpdir)
            result = await node._preview_file(str(f))
            assert result["type"] == "text"
            assert "Hello World" in result["content"]

    @pytest.mark.asyncio
    async def test_preview_code_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            f = Path(tmpdir, "test.py")
            f.write_text("print('hello')")

            node = FilesNode(root_path=tmpdir)
            result = await node._preview_file(str(f))
            assert result["type"] == "code"

    @pytest.mark.asyncio
    async def test_preview_nonexistent(self):
        node = FilesNode()
        result = await node._preview_file("/nonexistent/file.txt")
        assert "error" in result


class TestFilesNodeSearch:

    def test_cosine_similarity(self):
        sim = FilesNode._cosine_similarity([1, 0], [1, 0])
        assert abs(sim - 1.0) < 0.001

    def test_cosine_similarity_orthogonal(self):
        sim = FilesNode._cosine_similarity([1, 0], [0, 1])
        assert abs(sim) < 0.001

    def test_cosine_similarity_empty(self):
        sim = FilesNode._cosine_similarity([], [])
        assert sim == 0.0

    @pytest.mark.asyncio
    async def test_no_delete_action_without_confirmation(self):
        node = FilesNode()
        result = await node.process({"action": "delete", "path": "/test"})
        assert result["requires_confirmation"] is True

    @pytest.mark.asyncio
    async def test_unknown_action(self):
        node = FilesNode()
        result = await node.process({"action": "unknown"})
        assert "error" in result
