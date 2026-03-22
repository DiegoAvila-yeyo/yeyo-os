"""Tests para Git Integration — Micro-fase 5.9"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.nodes.code.git_service import GitService, GitStatus, GitCommitInfo


class TestGitStatus:

    @pytest.mark.asyncio
    async def test_status_parsing(self):
        service = GitService()
        service._run = AsyncMock(side_effect=[
            "main\n",  # branch
            "M  file1.py\n?? new_file.py\nA  staged.py\n",  # status
        ])
        status = await service.status()
        assert status.branch == "main"
        assert "staged.py" in status.staged
        assert "new_file.py" in status.untracked

    @pytest.mark.asyncio
    async def test_status_empty_repo(self):
        service = GitService()
        service._run = AsyncMock(side_effect=[
            "main\n",
            "\n",
        ])
        status = await service.status()
        assert status.branch == "main"
        assert len(status.staged) == 0
        assert len(status.modified) == 0


class TestGitCommit:

    @pytest.mark.asyncio
    async def test_commit(self):
        service = GitService()
        service._run = AsyncMock(side_effect=[
            "",  # git commit
            "abc1234\n",  # git rev-parse
        ])
        result = await service.commit("feat: add feature")
        assert result["hash"] == "abc1234"
        assert result["message"] == "feat: add feature"

    @pytest.mark.asyncio
    async def test_commit_message_truncated(self):
        service = GitService()
        service._run = AsyncMock(side_effect=["", "abc1234\n"])
        long_msg = "a" * 100
        result = await service.commit(long_msg)
        assert len(result["message"]) <= 72

    @pytest.mark.asyncio
    async def test_generate_commit_message(self):
        service = GitService()
        mock_provider = MagicMock()
        mock_provider.generate = AsyncMock(return_value=MagicMock(
            content="feat: add user authentication"
        ))
        mock_module = MagicMock()
        mock_module.OllamaProvider = MagicMock(return_value=mock_provider)
        with patch.dict("sys.modules", {"src.ia.ollama_provider": mock_module}):
            msg = await service.generate_commit_message("+ def login():")
            assert len(msg) <= 72
            assert "feat" in msg


class TestGitOperations:

    @pytest.mark.asyncio
    async def test_add_files(self):
        service = GitService()
        service._run = AsyncMock(return_value="")
        result = await service.add(["file1.py", "file2.py"])
        assert result["staged"] == ["file1.py", "file2.py"]

    @pytest.mark.asyncio
    async def test_diff(self):
        service = GitService()
        service._run = AsyncMock(return_value="+ new line\n- old line\n")
        diff = await service.diff()
        assert "+ new line" in diff

    @pytest.mark.asyncio
    async def test_diff_staged(self):
        service = GitService()
        service._run = AsyncMock(return_value="staged diff")
        diff = await service.diff(staged=True)
        assert "staged diff" in diff

    @pytest.mark.asyncio
    async def test_log(self):
        service = GitService()
        service._run = AsyncMock(return_value=(
            "abc123full|abc1234|feat: add feature|Author|2026-03-22\n"
            "def456full|def4567|fix: bug fix|Author|2026-03-21\n"
        ))
        commits = await service.log(limit=2)
        assert len(commits) == 2
        assert commits[0].short_hash == "abc1234"
        assert commits[1].message == "fix: bug fix"


class TestGitBranches:

    @pytest.mark.asyncio
    async def test_branch_list(self):
        service = GitService()
        service._run = AsyncMock(return_value="main\nfeature\ndevelop\n")
        branches = await service.branch_list()
        assert "main" in branches
        assert len(branches) == 3

    @pytest.mark.asyncio
    async def test_branch_create(self):
        service = GitService()
        service._run = AsyncMock(return_value="")
        result = await service.branch_create("feature-new")
        assert result["branch"] == "feature-new"
        assert result["created"] is True

    @pytest.mark.asyncio
    async def test_branch_switch(self):
        service = GitService()
        service._run = AsyncMock(return_value="")
        result = await service.branch_switch("develop")
        assert result["branch"] == "develop"
        assert result["switched"] is True
