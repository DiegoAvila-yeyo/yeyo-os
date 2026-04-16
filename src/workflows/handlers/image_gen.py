"""YeyoOS — Image Generation workflow handler."""

import logging
import os

logger = logging.getLogger("yeyoos.workflows.handlers.image_gen")


async def handle_image_gen(config: dict, variables: dict) -> dict:
    """Generate an image from a text prompt.

    Config:
        prompt (str): Text description of the image to generate.
        provider (str): Generation backend — ``"fal"`` (default).
        width (int): Image width in pixels (default 1024).
        height (int): Image height in pixels (default 1024).

    Returns:
        dict with ``image_url`` and ``prompt``.
    """
    prompt: str = config.get("prompt", "")
    provider: str = config.get("provider", "fal")
    width: int = config.get("width", 1024)
    height: int = config.get("height", 1024)

    if not prompt:
        return {"error": "prompt is required"}

    try:
        # Try the internal ImageGenerationNode first
        from src.nodes.image.generation import ImageGenerationNode

        node = ImageGenerationNode()
        await node.initialize()
        result = await node.process({
            "action": "generate",
            "prompt": prompt,
            "resolution": f"{width}x{height}",
        })
        await node.cleanup()
        url = result.get("image_url") or result.get("url", "")
        logger.info("Image generated via ImageGenerationNode: %s", url)
        return {"image_url": url, "prompt": prompt}

    except (ImportError, ModuleNotFoundError):
        logger.debug("ImageGenerationNode not available, falling back to httpx/fal")

    try:
        import httpx

        fal_key = os.getenv("FAL_KEY", "")
        if not fal_key:
            return {"error": "FAL_KEY environment variable is not set"}

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                "https://fal.run/fal-ai/flux/dev",
                headers={
                    "Authorization": f"Key {fal_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "prompt": prompt,
                    "image_size": {"width": width, "height": height},
                },
            )
            resp.raise_for_status()
            data = resp.json()

        url = ""
        if isinstance(data.get("images"), list) and data["images"]:
            url = data["images"][0].get("url", "")
        elif isinstance(data.get("image"), dict):
            url = data["image"].get("url", "")

        logger.info("Image generated via fal.ai: %s", url)
        return {"image_url": url, "prompt": prompt}

    except Exception as e:
        logger.exception("Image generation failed")
        return {"error": str(e)}
