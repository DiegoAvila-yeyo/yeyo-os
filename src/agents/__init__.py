"""
YeyoOS Agents Module
Arquitectura de agentes especializados que guían a Ollama.
"""

from .base import Agent, AgentInput, AgentOutput, GenericAgent
from .code_review import CodeReviewAgent
from .viral_content import ViralContentAgent
from .image_analysis import ImageAnalysisAgent
from .thumbnail import ThumbnailAgent
from .video_editing import VideoEditingAgent
from .content_analysis import ContentAnalysisAgent
from .conversation import ConversationAgent

__all__ = [
    "Agent",
    "AgentInput", 
    "AgentOutput",
    "GenericAgent",
    "CodeReviewAgent",
    "ViralContentAgent",
    "ImageAnalysisAgent",
    "ThumbnailAgent",
    "VideoEditingAgent",
    "ContentAnalysisAgent",
    "ConversationAgent",
]
