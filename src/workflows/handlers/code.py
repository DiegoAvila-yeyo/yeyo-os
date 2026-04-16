"""YeyoOS — Sandboxed code execution workflow handler."""

import asyncio
import logging
import os
import subprocess
import tempfile

logger = logging.getLogger("yeyoos.workflows.handlers.code")


async def handle_code(config: dict, variables: dict) -> dict:
    """Execute Python code in a sandboxed subprocess.

    The code is written to a temporary file and executed in a fresh Python
    subprocess with a hard timeout.  **Never** executed in the current
    process.

    Config:
        code (str): Python source code to execute.
        timeout (int): Maximum execution time in seconds (default 30).

    Returns:
        dict with ``stdout``, ``stderr``, and ``return_code``.
    """
    code: str = config.get("code", "")
    timeout: int = config.get("timeout", 30)

    if not code:
        return {"error": "code is required"}

    try:
        loop = asyncio.get_running_loop()

        def _run() -> dict:
            fd, path = tempfile.mkstemp(suffix=".py", prefix="yeyoos_code_")
            try:
                with os.fdopen(fd, "w") as fh:
                    fh.write(code)

                result = subprocess.run(
                    ["python", path],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env={
                        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
                        "HOME": os.environ.get("HOME", "/nonexistent"),
                        "LANG": "en_US.UTF-8",
                    },
                )
                return {
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                    "return_code": result.returncode,
                }
            except subprocess.TimeoutExpired:
                return {
                    "stdout": "",
                    "stderr": f"Execution timed out after {timeout}s",
                    "return_code": -1,
                }
            finally:
                try:
                    os.unlink(path)
                except OSError:
                    pass

        result = await loop.run_in_executor(None, _run)
        logger.info("Code executed — return_code=%s", result["return_code"])
        return result

    except Exception as e:
        logger.exception("Code execution handler failed")
        return {"error": str(e)}
