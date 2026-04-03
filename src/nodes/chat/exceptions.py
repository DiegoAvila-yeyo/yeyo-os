"""
ChatNodeService Integration - Custom Exceptions

Specific exceptions for clear error handling and logging.
"""


class ChatNodeServiceException(Exception):
    """Base exception for ChatNodeService."""
    pass


# Input validation errors
class InvalidInputError(ChatNodeServiceException):
    """Input validation failed."""
    pass


class MessageEmptyError(InvalidInputError):
    """Message is empty."""
    pass


class MessageTooLongError(InvalidInputError):
    """Message exceeds length limit."""
    pass


class InvalidConversationIdError(InvalidInputError):
    """Conversation ID doesn't exist."""
    pass


class InvalidToneError(InvalidInputError):
    """Tone is not a valid ConversationTone."""
    pass


class InvalidTypeError(InvalidInputError):
    """Conversation type is not a valid ConversationType."""
    pass


# Agent errors
class AgentValidationError(ChatNodeServiceException):
    """Agent validation (input or output) failed."""
    pass


class SystemPromptGenerationError(ChatNodeServiceException):
    """Agent failed to generate system prompt."""
    pass


# Ollama/LLM errors
class OllamaError(ChatNodeServiceException):
    """Generic Ollama/LLM error."""
    pass


class OllamaUnreachableError(OllamaError):
    """Cannot connect to Ollama."""
    pass


class OllamaTimeoutError(OllamaError):
    """Ollama request timed out."""
    pass


class OllamaOutOfMemoryError(OllamaError):
    """Ollama ran out of memory."""
    pass


class OllamaInvalidResponseError(OllamaError):
    """Ollama returned invalid response."""
    pass


# Output errors
class OutputValidationError(ChatNodeServiceException):
    """Output validation failed."""
    pass


class InvalidConfidenceError(OutputValidationError):
    """Confidence score is invalid."""
    pass


# System errors
class DatabaseError(ChatNodeServiceException):
    """Database operation failed."""
    pass


class MemoryInjectionError(ChatNodeServiceException):
    """Failed to inject memory context."""
    pass


class InternalServerError(ChatNodeServiceException):
    """Unexpected internal error."""
    pass


# Rate limiting
class RateLimitExceededError(ChatNodeServiceException):
    """Rate limit exceeded."""
    pass


# Timeout
class RequestTimeoutError(ChatNodeServiceException):
    """Request took too long."""
    pass
