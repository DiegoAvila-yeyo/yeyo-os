"""YeyoOS — Workflow Handlers Package."""

from src.workflows.handlers.chat import handle_chat
from src.workflows.handlers.code import handle_code
from src.workflows.handlers.file_io import handle_file_read, handle_file_write
from src.workflows.handlers.filter import handle_filter
from src.workflows.handlers.http import handle_http_request
from src.workflows.handlers.image_gen import handle_image_gen
from src.workflows.handlers.memory import handle_memory_read, handle_memory_write
from src.workflows.handlers.slideshow import handle_slideshow
from src.workflows.handlers.video_gen import handle_video_gen

__all__ = [
    "handle_chat",
    "handle_code",
    "handle_file_read",
    "handle_file_write",
    "handle_filter",
    "handle_http_request",
    "handle_image_gen",
    "handle_memory_read",
    "handle_memory_write",
    "handle_slideshow",
    "handle_video_gen",
]
