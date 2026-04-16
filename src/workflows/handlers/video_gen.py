"""YeyoOS — Video Generation workflow handler."""

import logging

logger = logging.getLogger("yeyoos.workflows.handlers.video_gen")


async def handle_video_gen(config: dict, variables: dict) -> dict:
    """Generate a video from a text prompt.

    Config:
        prompt (str): Text description of the video to generate.
        provider (str): Generation backend — ``"replicate"`` (default).
        duration (int): Video duration in seconds (default 5).

    Returns:
        dict with ``video_url`` and ``prompt``.
    """
    prompt: str = config.get("prompt", "")
    provider: str = config.get("provider", "replicate")
    duration: int = config.get("duration", 5)

    if not prompt:
        return {"error": "prompt is required"}

    try:
        from src.nodes.video.generation import VideoGenerationService

        service = VideoGenerationService()
        job = await service.generate_video(
            image_path="",
            prompt=prompt,
            duration=float(duration),
            preferred_provider=provider,
        )

        url = getattr(job, "output_url", "") or getattr(job, "video_url", "") or ""
        status = getattr(job, "status", None)
        logger.info(
            "Video generation job %s — status=%s url=%s",
            getattr(job, "id", "?"),
            status,
            url,
        )
        return {"video_url": url, "prompt": prompt}

    except (ImportError, ModuleNotFoundError):
        logger.debug("VideoGenerationService not available")
        return {"error": "VideoGenerationService is not available and no fallback configured"}

    except Exception as e:
        logger.exception("Video generation failed")
        return {"error": str(e)}
