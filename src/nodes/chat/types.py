"""
ChatNodeService Integration - Type Definitions

Type-safe interfaces for ChatNode ↔ ConversationAgent integration.
"""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime, timezone


class ConversationType(str, Enum):
    """Types of conversations the agent handles."""
    GENERAL = "general"
    SUPPORT = "support"
    INFO = "info"
    SALES = "sales"
    COACHING = "coaching"
    DEBUG = "debug"


class ConversationTone(str, Enum):
    """Tone of conversation."""
    PROFESSIONAL = "professional"
    CASUAL = "casual"
    FRIENDLY = "friendly"
    FORMAL = "formal"


class ErrorCode(str, Enum):
    """Standardized error codes."""
    # Input errors
    ERROR_INVALID_INPUT = "error_invalid_input"
    ERROR_MESSAGE_EMPTY = "error_message_empty"
    ERROR_MESSAGE_TOO_LONG = "error_message_too_long"
    ERROR_INVALID_CONVERSATION_ID = "error_invalid_conversation_id"
    ERROR_INVALID_TONE = "error_invalid_tone"
    ERROR_INVALID_TYPE = "error_invalid_type"
    
    # Agent errors
    ERROR_AGENT_VALIDATION_FAILED = "error_agent_validation_failed"
    ERROR_SYSTEM_PROMPT_GENERATION = "error_system_prompt_generation"
    
    # Ollama errors
    ERROR_OLLAMA_UNREACHABLE = "error_ollama_unreachable"
    ERROR_OLLAMA_TIMEOUT = "error_ollama_timeout"
    ERROR_OLLAMA_OUT_OF_MEMORY = "error_ollama_out_of_memory"
    ERROR_OLLAMA_INVALID_RESPONSE = "error_ollama_invalid_response"
    
    # Output errors
    ERROR_OUTPUT_VALIDATION_FAILED = "error_output_validation_failed"
    ERROR_INVALID_CONFIDENCE = "error_invalid_confidence"
    
    # System errors
    ERROR_DATABASE = "error_database"
    ERROR_MEMORY_INJECTION = "error_memory_injection"
    ERROR_INTERNAL_SERVER_ERROR = "error_internal_server_error"
    
    # Rate limiting
    ERROR_RATE_LIMIT_EXCEEDED = "error_rate_limit_exceeded"
    
    # Timeout
    ERROR_REQUEST_TIMEOUT = "error_request_timeout"


@dataclass
class ChatNodeInput:
    """
    Input to ChatNode.process() from ChatNode.
    
    All fields validated before processing.
    """
    message: str
    conversation_id: Optional[str] = None
    tone: ConversationTone = ConversationTone.PROFESSIONAL
    conversation_type: ConversationType = ConversationType.GENERAL
    user_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate field types."""
        if not isinstance(self.message, str):
            raise TypeError(f"message must be str, got {type(self.message)}")
        if self.conversation_id is not None and not isinstance(self.conversation_id, str):
            raise TypeError(f"conversation_id must be str or None, got {type(self.conversation_id)}")
        if not isinstance(self.tone, ConversationTone):
            raise TypeError(f"tone must be ConversationTone, got {type(self.tone)}")
        if not isinstance(self.conversation_type, ConversationType):
            raise TypeError(f"conversation_type must be ConversationType, got {type(self.conversation_type)}")


@dataclass
class ChatNodeOutput:
    """
    Output from ChatNode.process() - Success case.
    
    Contains response + metadata for monitoring and improvement.
    """
    response: str
    confidence: float
    reasoning: str
    suggestions: List[str] = field(default_factory=list)
    tokens_used: int = 0
    conversation_id: str = ""
    message_id: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate fields."""
        if not isinstance(self.response, str):
            raise TypeError(f"response must be str, got {type(self.response)}")
        if not isinstance(self.confidence, (int, float)):
            raise TypeError(f"confidence must be float, got {type(self.confidence)}")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be in [0.0, 1.0], got {self.confidence}")
        if not isinstance(self.reasoning, str):
            raise TypeError(f"reasoning must be str, got {type(self.reasoning)}")
        if not isinstance(self.suggestions, list):
            raise TypeError(f"suggestions must be list, got {type(self.suggestions)}")
        if not isinstance(self.tokens_used, int):
            raise TypeError(f"tokens_used must be int, got {type(self.tokens_used)}")


@dataclass
class ChatNodeError:
    """
    Output from ChatNode.process() - Error case.
    
    Contains error info for debugging without exposing system details.
    """
    error: str
    error_code: ErrorCode
    conversation_id: Optional[str] = None
    user_id: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self):
        """Validate fields."""
        if not isinstance(self.error, str):
            raise TypeError(f"error must be str, got {type(self.error)}")
        if not isinstance(self.error_code, ErrorCode):
            raise TypeError(f"error_code must be ErrorCode, got {type(self.error_code)}")


@dataclass
class ConversationContext:
    """
    Full context for a conversation session.
    
    Used by agent to understand conversation flow.
    """
    conversation_id: str
    user_id: Optional[str]
    conversation_type: ConversationType
    tone: ConversationTone
    message_count: int
    history_last_20_messages: List[Dict[str, str]] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    conversation_duration_seconds: int = 0
    average_response_time_ms: float = 0.0
    previous_confidence_scores: List[float] = field(default_factory=list)
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """Get statistics about this conversation."""
        return {
            "message_count": self.message_count,
            "duration_seconds": self.conversation_duration_seconds,
            "avg_response_time_ms": self.average_response_time_ms,
            "avg_confidence": (
                sum(self.previous_confidence_scores) / len(self.previous_confidence_scores)
                if self.previous_confidence_scores else 0.0
            ),
            "history_length": len(self.history_last_20_messages),
        }


@dataclass
class ValidationResult:
    """Result of input validation."""
    is_valid: bool
    error_code: Optional[ErrorCode] = None
    error_message: Optional[str] = None
    
    def __post_init__(self):
        """Ensure consistency."""
        if self.is_valid:
            if self.error_code is not None or self.error_message is not None:
                raise ValueError("Valid result cannot have error_code or error_message")
        else:
            if self.error_code is None or self.error_message is None:
                raise ValueError("Invalid result must have error_code and error_message")
