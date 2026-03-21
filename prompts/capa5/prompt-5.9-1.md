## ═══════════════════════════════════════
## MICRO-FASE 5.9 — Code Node (Git Integration)
## Tipo: VSCODE | Prompts: 1 | Complejidad: Media
## ═══════════════════════════════════════

### PROMPT 5.9-1 [VSCODE] — Integración Git con commit messages generados por IA

```
Estamos construyendo YeyoOS, un OS AI-nativo con arquitectura hexagonal. Esta es la micro-fase 5.9 de Capa 5 (Órganos): añadir integración Git al Code Node con mensajes de commit generados por IA.

CONTEXTO:
- Micro-fases 5.7-5.8 completadas: CodeNode con editor y sandbox
- Git: add, commit, push, pull, diff, log
- IA genera mensajes de commit desde cambios staged
- Branch management: create, switch, list
- Usa git CLI via subprocess
- Hardware: GTX 1060 3GB VRAM, 16GB RAM

Abre el directorio ~/yeyo-os en VS Code.

CREAR:

1. Crear archivo src/nodes/code/git_service.py:

   Ruta: ~/yeyo-os/src/nodes/code/git_service.py
   Contenido:

   """
   YeyoOS — Git Integration Service
   Micro-fase 5.9 — Capa 5: Órganos

   Operaciones Git con mensajes de commit generados por IA.
   """

   import asyncio
   from typing import Optional
   from dataclasses import dataclass, field
   from datetime import datetime, timezone


   @dataclass
   class GitStatus:
       """Estado del repositorio Git."""
       branch: str
       staged: list[str] = field(default_factory=list)
       modified: list[str] = field(default_factory=list)
       untracked: list[str] = field(default_factory=list)
       ahead: int = 0
       behind: int = 0


   @dataclass
   class GitCommitInfo:
       """Información de un commit."""
       hash: str
       message: str
       author: str
       date: str


   class GitService:
       """Servicio de operaciones Git con asistencia IA."""

       def __init__(self, repo_path: str):
           self._repo_path = repo_path

       async def status(self) -> GitStatus:
           """Obtiene estado del repositorio."""
           output = await self._run_git("status", "--porcelain", "-b")
           lines = output.strip().split("\n") if output.strip() else []

           branch = "main"
           staged, modified, untracked = [], [], []

           for line in lines:
               if line.startswith("## "):
                   branch = line[3:].split("...")[0]
               elif line.startswith("A  ") or line.startswith("M  "):
                   staged.append(line[3:].strip())
               elif line.startswith(" M "):
                   modified.append(line[3:].strip())
               elif line.startswith("?? "):
                   untracked.append(line[3:].strip())

           return GitStatus(
               branch=branch,
               staged=staged,
               modified=modified,
               untracked=untracked,
           )

       async def add(self, files: list[str]) -> dict:
           """Añade archivos al staging area."""
           if not files:
               return {"error": "No files specified"}
           args = ["add"] + files
           output = await self._run_git(*args)
           return {"added": files, "output": output}

       async def commit(self, message: Optional[str] = None) -> dict:
           """
           Hace commit. Si no se proporciona mensaje, IA lo genera.
           """
           if not message:
               message = await self._generate_commit_message()

           output = await self._run_git("commit", "-m", message)
           return {"message": message, "output": output}

       async def push(self, remote: str = "origin", branch: Optional[str] = None) -> dict:
           """Push al remoto."""
           if branch is None:
               status = await self.status()
               branch = status.branch
           output = await self._run_git("push", remote, branch)
           return {"remote": remote, "branch": branch, "output": output}

       async def pull(self, remote: str = "origin", branch: Optional[str] = None) -> dict:
           """Pull del remoto."""
           if branch is None:
               status = await self.status()
               branch = status.branch
           output = await self._run_git("pull", remote, branch)
           return {"remote": remote, "branch": branch, "output": output}

       async def diff(self, staged: bool = False) -> str:
           """Muestra diff de cambios."""
           args = ["diff"]
           if staged:
               args.append("--staged")
           return await self._run_git(*args)

       async def log(self, limit: int = 10) -> list[GitCommitInfo]:
           """Obtiene historial de commits."""
           output = await self._run_git(
               "log", f"--max-count={limit}",
               "--format=%H|%s|%an|%ai",
           )
           commits = []
           for line in output.strip().split("\n"):
               if "|" in line:
                   parts = line.split("|", 3)
                   if len(parts) == 4:
                       commits.append(GitCommitInfo(
                           hash=parts[0][:8],
                           message=parts[1],
                           author=parts[2],
                           date=parts[3],
                       ))
           return commits

       async def create_branch(self, name: str) -> dict:
           """Crea nueva branch."""
           output = await self._run_git("checkout", "-b", name)
           return {"branch": name, "output": output}

       async def switch_branch(self, name: str) -> dict:
           """Cambia a branch existente."""
           output = await self._run_git("checkout", name)
           return {"branch": name, "output": output}

       async def list_branches(self) -> list[str]:
           """Lista branches."""
           output = await self._run_git("branch", "--list")
           return [b.strip().lstrip("* ") for b in output.strip().split("\n") if b.strip()]

       # ═══════════════════════════════════
       # IA COMMIT MESSAGE
       # ═══════════════════════════════════

       async def _generate_commit_message(self) -> str:
           """Genera mensaje de commit con IA a partir del diff staged."""
           diff_output = await self.diff(staged=True)

           if not diff_output.strip():
               return "chore: empty commit"

           from src.ia.ollama_provider import OllamaProvider
           provider = OllamaProvider()
           response = await provider.generate(
               prompt=f"Generate a concise git commit message for these changes:\n\n{diff_output[:2000]}",
               system="You are a git expert. Generate commit messages following Conventional Commits format "
                      "(feat:, fix:, docs:, chore:, refactor:, test:). "
                      "Keep it under 72 characters. Only return the message, nothing else.",
               temperature=0.3,
           )
           return response.content.strip()[:72]

       async def _run_git(self, *args: str) -> str:
           """Ejecuta comando git."""
           process = await asyncio.create_subprocess_exec(
               "git", *args,
               cwd=self._repo_path,
               stdout=asyncio.subprocess.PIPE,
               stderr=asyncio.subprocess.PIPE,
           )
           stdout, stderr = await asyncio.wait_for(
               process.communicate(), timeout=30,
           )
           if process.returncode != 0:
               raise RuntimeError(f"Git error: {stderr.decode()}")
           return stdout.decode()

2. Actualizar src/nodes/code/__init__.py:

   Ruta: ~/yeyo-os/src/nodes/code/__init__.py
   Contenido:
   from .service import CodeNode
   from .sandbox import CodeSandbox, SandboxResult
   from .git_service import GitService

3. Crear archivo tests/unit/nodes/code/test_git_service.py:

   Ruta: ~/yeyo-os/tests/unit/nodes/code/test_git_service.py
   Contenido:

   """Tests para Git Service — Micro-fase 5.9"""

   import pytest
   from unittest.mock import AsyncMock, patch, MagicMock
   from src.nodes.code.git_service import GitService, GitStatus, GitCommitInfo


   class TestGitStatus:

       @pytest.mark.asyncio
       async def test_status_parses_branch(self):
           service = GitService("/fake/repo")
           service._run_git = AsyncMock(return_value="## main...origin/main\n")
           status = await service.status()
           assert status.branch == "main"

       @pytest.mark.asyncio
       async def test_status_parses_staged(self):
           service = GitService("/fake/repo")
           service._run_git = AsyncMock(
               return_value="## main\nA  new_file.py\nM  changed.py\n"
           )
           status = await service.status()
           assert "new_file.py" in status.staged

       @pytest.mark.asyncio
       async def test_status_parses_untracked(self):
           service = GitService("/fake/repo")
           service._run_git = AsyncMock(
               return_value="## main\n?? untracked.txt\n"
           )
           status = await service.status()
           assert "untracked.txt" in status.untracked


   class TestGitOperations:

       @pytest.mark.asyncio
       async def test_add_files(self):
           service = GitService("/fake/repo")
           service._run_git = AsyncMock(return_value="")
           result = await service.add(["file1.py", "file2.py"])
           assert result["added"] == ["file1.py", "file2.py"]

       @pytest.mark.asyncio
       async def test_add_empty_returns_error(self):
           service = GitService("/fake/repo")
           result = await service.add([])
           assert "error" in result

       @pytest.mark.asyncio
       async def test_commit_with_message(self):
           service = GitService("/fake/repo")
           service._run_git = AsyncMock(return_value="[main abc123] my message\n")
           result = await service.commit("my message")
           assert result["message"] == "my message"

       @pytest.mark.asyncio
       async def test_commit_ai_generated_message(self):
           service = GitService("/fake/repo")
           service._run_git = AsyncMock(return_value="")
           service.diff = AsyncMock(return_value="+ new line")

           mock_provider = MagicMock()
           mock_provider.generate = AsyncMock(return_value=MagicMock(
               content="feat: add new feature"
           ))
           with patch("src.nodes.code.git_service.OllamaProvider", return_value=mock_provider):
               result = await service.commit()
               assert "feat:" in result["message"]

       @pytest.mark.asyncio
       async def test_log_parses_commits(self):
           service = GitService("/fake/repo")
           service._run_git = AsyncMock(
               return_value="abc12345|feat: new|John|2024-01-01\ndef67890|fix: bug|Jane|2024-01-02\n"
           )
           commits = await service.log(limit=2)
           assert len(commits) == 2
           assert commits[0].message == "feat: new"
           assert commits[1].author == "Jane"

       @pytest.mark.asyncio
       async def test_diff_staged(self):
           service = GitService("/fake/repo")
           service._run_git = AsyncMock(return_value="+ added line\n- removed line\n")
           diff = await service.diff(staged=True)
           assert "+ added line" in diff

4. Ejecutar tests:
   cd ~/yeyo-os
   source .venv/bin/activate
   python -m pytest tests/unit/nodes/code/test_git_service.py -v

VERIFICAR:
- [ ] Git status parsea branch, staged, modified, untracked
- [ ] Git add añade archivos al staging
- [ ] Git commit funciona con mensaje manual y generado por IA
- [ ] IA genera mensajes en formato Conventional Commits
- [ ] Git log parsea historial correctamente
- [ ] Git diff muestra cambios (staged y no-staged)
- [ ] Branch management funciona
- [ ] TODOS los tests pasan

SI FALLA:
- Import error: verificar __init__.py actualizado
- Git no instalado: tests usan mocks
- OllamaProvider mock: verificar patch path

NO HACER:
- No ejecutar git real en tests (usar mocks)
- No implementar merge/rebase (demasiado complejo para v1)
- No exponer credenciales Git

GATE: GitService con operaciones Git, commit messages por IA (Conventional Commits), branch management, diff, log, todos los tests pasan.
```
