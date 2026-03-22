"""
YeyoOS — Git Integration Service
Micro-fase 5.9 — Capa 5: Órganos

Integración con Git: status, add, commit, push, pull, diff, log, branches.
Commit messages generados por IA en formato Conventional Commits.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class GitStatus:
    """Estado del repositorio Git."""
    branch: str = ""
    staged: list[str] = field(default_factory=list)
    modified: list[str] = field(default_factory=list)
    untracked: list[str] = field(default_factory=list)
    ahead: int = 0
    behind: int = 0


@dataclass
class GitCommitInfo:
    """Información de un commit."""
    hash: str
    short_hash: str
    message: str
    author: str
    date: str


class GitService:
    """
    Servicio de integración con Git.
    Usa git CLI via subprocess.
    """

    def __init__(self, repo_path: str = "."):
        self._repo_path = repo_path

    async def status(self) -> GitStatus:
        """Obtiene status del repositorio."""
        result = GitStatus()

        # Branch
        branch_out = await self._run("git rev-parse --abbrev-ref HEAD")
        result.branch = branch_out.strip()

        # Porcelain status
        status_out = await self._run("git status --porcelain")
        for line in status_out.strip().split("\n"):
            if not line.strip():
                continue
            code = line[:2]
            filepath = line[3:].strip()

            if code[0] in ("A", "M", "D", "R"):
                result.staged.append(filepath)
            if code[1] == "M":
                result.modified.append(filepath)
            if code == "??":
                result.untracked.append(filepath)

        return result

    async def add(self, files: list[str]) -> dict:
        """Agrega archivos al staging area."""
        files_str = " ".join(f'"{f}"' for f in files)
        await self._run(f"git add {files_str}")
        return {"staged": files}

    async def commit(self, message: str) -> dict:
        """Crea un commit con el mensaje dado."""
        if len(message) > 72:
            message = message[:72]
        await self._run(f'git commit -m "{message}"')
        hash_out = await self._run("git rev-parse --short HEAD")
        return {"hash": hash_out.strip(), "message": message}

    async def generate_commit_message(self, diff: str) -> str:
        """Genera commit message con IA en formato Conventional Commits."""
        from src.ia.ollama_provider import OllamaProvider
        provider = OllamaProvider()
        response = await provider.generate(
            prompt=f"Generate a git commit message for this diff in Conventional Commits format "
                   f"(feat:, fix:, docs:, refactor:, test:, chore:). "
                   f"Max 72 chars. Only return the message.\n\nDiff:\n{diff[:2000]}",
            system="You are a git expert. Write concise commit messages in Conventional Commits format. Max 72 chars.",
            temperature=0.3,
        )
        msg = response.content.strip().strip('"').strip("'")
        return msg[:72]

    async def diff(self, staged: bool = False) -> str:
        """Muestra diff de cambios."""
        cmd = "git diff --staged" if staged else "git diff"
        return await self._run(cmd)

    async def log(self, limit: int = 10) -> list[GitCommitInfo]:
        """Muestra historial de commits."""
        fmt = "--pretty=format:%H|%h|%s|%an|%ad"
        out = await self._run(f"git log {fmt} --date=short -n {limit}")
        commits = []
        for line in out.strip().split("\n"):
            if not line.strip():
                continue
            parts = line.split("|", 4)
            if len(parts) == 5:
                commits.append(GitCommitInfo(
                    hash=parts[0], short_hash=parts[1],
                    message=parts[2], author=parts[3], date=parts[4],
                ))
        return commits

    async def branch_list(self) -> list[str]:
        """Lista branches."""
        out = await self._run("git branch --format='%(refname:short)'")
        return [b.strip().strip("'") for b in out.strip().split("\n") if b.strip()]

    async def branch_create(self, name: str) -> dict:
        """Crea una nueva branch."""
        await self._run(f"git checkout -b {name}")
        return {"branch": name, "created": True}

    async def branch_switch(self, name: str) -> dict:
        """Cambia a otra branch."""
        await self._run(f"git checkout {name}")
        return {"branch": name, "switched": True}

    async def push(self) -> dict:
        """Push al remote."""
        out = await self._run("git push")
        return {"pushed": True, "output": out.strip()}

    async def pull(self) -> dict:
        """Pull del remote."""
        out = await self._run("git pull")
        return {"pulled": True, "output": out.strip()}

    async def _run(self, command: str) -> str:
        """Ejecuta comando git."""
        process = await asyncio.create_subprocess_shell(
            command,
            cwd=self._repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(
            process.communicate(), timeout=30,
        )
        if process.returncode != 0:
            error = stderr.decode("utf-8", errors="replace")
            raise RuntimeError(f"Git error: {error}")
        return stdout.decode("utf-8", errors="replace")
