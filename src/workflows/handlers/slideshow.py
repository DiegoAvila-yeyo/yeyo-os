"""YeyoOS — Slideshow (image-to-video) workflow handler."""

import logging
import os

logger = logging.getLogger("yeyoos.workflows.handlers.slideshow")


async def handle_slideshow(config: dict, variables: dict) -> dict:
    """Compose a slideshow video from a list of images.

    Config:
        images (list[str]): URLs or local paths of images.
        duration_per_image (float): Seconds each image is shown (default 3.0).
        output_path (str): Destination file path for the rendered video.

    Returns:
        dict with ``video_path``.
    """
    images: list = config.get("images", [])
    duration_per_image: float = config.get("duration_per_image", 3.0)
    output_path: str = config.get("output_path", "")

    if not images:
        return {"error": "images list is required and must not be empty"}
    if not output_path:
        return {"error": "output_path is required"}

    # Try VideoComposerService first
    try:
        from src.nodes.video.composer import VideoComposerService

        composer = VideoComposerService()
        result = await composer.compose(
            images=images,
            duration_per_image=duration_per_image,
            output_path=output_path,
        )
        path = result if isinstance(result, str) else result.get("video_path", output_path)
        logger.info("Slideshow composed via VideoComposerService: %s", path)
        return {"video_path": path}

    except (ImportError, ModuleNotFoundError):
        logger.debug("VideoComposerService not available, falling back to moviepy")

    # Fallback: build slideshow with moviepy v2
    try:
        import asyncio
        import functools
        import tempfile

        import httpx
        from moviepy import ImageClip, concatenate_videoclips

        async def _download_if_url(src: str, client: httpx.AsyncClient) -> str:
            """Download a remote image to a local temp file if needed."""
            if src.startswith(("http://", "https://")):
                resp = await client.get(src)
                resp.raise_for_status()
                ext = os.path.splitext(src.split("?")[0])[-1] or ".png"
                tmp = tempfile.NamedTemporaryFile(suffix=ext, delete=False)
                tmp.write(resp.content)
                tmp.close()
                return tmp.name
            return src

        local_paths: list[str] = []
        async with httpx.AsyncClient(timeout=60.0) as client:
            for img in images:
                local_paths.append(await _download_if_url(img, client))

        def _render() -> str:
            clips = [
                ImageClip(p).with_duration(duration_per_image)
                for p in local_paths
            ]
            video = concatenate_videoclips(clips, method="compose")
            video.write_videofile(output_path, fps=24, logger=None)
            video.close()
            for c in clips:
                c.close()
            return output_path

        loop = asyncio.get_running_loop()
        path = await loop.run_in_executor(None, _render)
        logger.info("Slideshow rendered via moviepy: %s", path)
        return {"video_path": path}

    except Exception as e:
        logger.exception("Slideshow creation failed")
        return {"error": str(e)}
