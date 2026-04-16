"""YeyoOS — Chat / LLM workflow handler."""

import logging
import os

logger = logging.getLogger("yeyoos.workflows.handlers.chat")


async def handle_chat(config: dict, variables: dict) -> dict:
    """Send a prompt to an LLM and return the response.

    Config:
        prompt (str): The user prompt.
        model (str): Model name (default ``"qwen2.5-coder:7b"``).
        system (str, optional): System prompt prepended to the conversation.

    Returns:
        dict with ``response`` and ``model``.
    """
    prompt: str = config.get("prompt", "")
    model: str = config.get("model", "qwen2.5-coder:7b")
    system: str = config.get("system", "")

    if not prompt:
        return {"error": "prompt is required"}

    # Try the internal OllamaProvider first
    try:
        from src.ia.ollama_provider import OllamaProvider

        provider = OllamaProvider(model=model)
        ia_response = await provider.generate(prompt=prompt, system=system)
        text = ia_response.text if hasattr(ia_response, "text") else str(ia_response)
        await provider.close()
        logger.info("Chat response via OllamaProvider (model=%s)", model)
        return {"response": text, "model": model}

    except (ImportError, ModuleNotFoundError):
        logger.debug("OllamaProvider not available, falling back to httpx")

    # Fallback: direct HTTP call to Ollama API
    try:
        import httpx

        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

        payload: dict = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{ollama_host}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()

        text = data.get("response", "")
        logger.info("Chat response via Ollama HTTP (model=%s)", model)
        return {"response": text, "model": model}

    except Exception as e:
        logger.exception("Chat handler failed")
        return {"error": str(e)}
