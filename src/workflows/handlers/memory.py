"""YeyoOS — Memory read/write workflow handlers.

Sacred Rule: memories are **NEVER** deleted — only stored and recalled.
"""

import logging
import uuid

logger = logging.getLogger("yeyoos.workflows.handlers.memory")


async def handle_memory_read(config: dict, variables: dict) -> dict:
    """Recall memories matching a query.

    Config:
        query (str): Search query.
        limit (int): Maximum number of results (default 5).

    Returns:
        dict with ``memories`` list.
    """
    query: str = config.get("query", "")
    limit: int = config.get("limit", 5)

    if not query:
        return {"error": "query is required"}

    try:
        from src.memory.flash_memory import FlashMemory

        # Expect a pre-initialised FlashMemory instance in variables
        fm: FlashMemory | None = variables.get("_flash_memory")
        if fm is None:
            return {"error": "FlashMemory instance not found in execution variables (_flash_memory)"}

        results = await fm.recall(query=query, limit=limit)
        memories = [
            {
                "id": getattr(m, "id", str(i)),
                "content": getattr(m, "content", str(m)),
                "type": getattr(m, "type", "unknown"),
            }
            for i, m in enumerate(results)
        ]
        logger.info("Memory recall returned %d results for query=%r", len(memories), query)
        return {"memories": memories}

    except (ImportError, ModuleNotFoundError):
        logger.debug("FlashMemory not available")
        return {"error": "FlashMemory module is not available"}

    except Exception as e:
        logger.exception("Memory read failed")
        return {"error": str(e)}


async def handle_memory_write(config: dict, variables: dict) -> dict:
    """Store a new memory.  Memories are **never** deleted.

    Config:
        content (str): The content to store.
        memory_type (str): Category / type label (default ``"general"``).
        tags (list[str]): Optional tags (default ``[]``).

    Returns:
        dict with ``memory_id`` and ``stored`` flag.
    """
    content: str = config.get("content", "")
    memory_type: str = config.get("memory_type", "general")
    tags: list = config.get("tags", [])

    if not content:
        return {"error": "content is required"}

    try:
        from src.memory.flash_memory import FlashMemory

        fm: FlashMemory | None = variables.get("_flash_memory")
        if fm is None:
            return {"error": "FlashMemory instance not found in execution variables (_flash_memory)"}

        memory = await fm.store(
            content=content,
            type=memory_type,
            metadata={"tags": tags},
            source="workflow",
        )
        memory_id = getattr(memory, "id", str(uuid.uuid4()))
        logger.info("Memory stored id=%s type=%s", memory_id, memory_type)
        return {"memory_id": str(memory_id), "stored": True}

    except (ImportError, ModuleNotFoundError):
        logger.debug("FlashMemory not available")
        return {"error": "FlashMemory module is not available"}

    except Exception as e:
        logger.exception("Memory write failed")
        return {"error": str(e)}
