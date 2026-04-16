"""YeyoOS — File I/O workflow handlers with path-traversal protection."""

import logging
import os

logger = logging.getLogger("yeyoos.workflows.handlers.file_io")

# Directories that file handlers are allowed to access.
_ALLOWED_ROOTS: tuple[str, ...] = (
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")),  # project root
)


def _validate_path(path: str) -> str | None:
    """Return an error message if *path* is unsafe, else ``None``."""
    if ".." in path.split(os.sep):
        return "Path traversal detected: '..' segments are not allowed"
    abs_path = os.path.realpath(path)
    if not any(abs_path.startswith(os.path.realpath(root)) for root in _ALLOWED_ROOTS):
        return f"Path is outside allowed directories: {abs_path}"
    return None


async def handle_file_read(config: dict, variables: dict) -> dict:
    """Read a file from disk.

    Config:
        path (str): File path to read.

    Returns:
        dict with ``content`` and ``path``.
    """
    path: str = config.get("path", "")
    if not path:
        return {"error": "path is required"}

    try:
        err = _validate_path(path)
        if err:
            return {"error": err}

        abs_path = os.path.realpath(path)
        if not os.path.isfile(abs_path):
            return {"error": f"File not found: {abs_path}"}

        with open(abs_path, "r", encoding="utf-8") as fh:
            content = fh.read()

        logger.info("File read: %s (%d bytes)", abs_path, len(content))
        return {"content": content, "path": abs_path}

    except Exception as e:
        logger.exception("File read failed")
        return {"error": str(e)}


async def handle_file_write(config: dict, variables: dict) -> dict:
    """Write content to a file.

    Config:
        path (str): Destination file path.
        content (str): Content to write.

    Returns:
        dict with ``path`` and ``written`` flag.
    """
    path: str = config.get("path", "")
    content: str = config.get("content", "")

    if not path:
        return {"error": "path is required"}

    try:
        err = _validate_path(path)
        if err:
            return {"error": err}

        abs_path = os.path.realpath(path)

        os.makedirs(os.path.dirname(abs_path), exist_ok=True)

        with open(abs_path, "w", encoding="utf-8") as fh:
            fh.write(content)

        logger.info("File written: %s (%d bytes)", abs_path, len(content))
        return {"path": abs_path, "written": True}

    except Exception as e:
        logger.exception("File write failed")
        return {"error": str(e)}
