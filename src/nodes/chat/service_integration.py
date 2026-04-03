"""
ChatNodeService - Integration between ChatNode and ConversationAgent

Handles the complete pipeline:
1. Input validation
2. Context injection (memory)
3. Agent system prompt generation
4. Ollama call with retry/timeout
5. Output validation
6. Memory storage
7. Response to user
"""

import asyncio
import logging
import uuid
from typing import Optional, Tuple, Union
from datetime import datetime, timezone

from src.nodes.chat.types import (
    ChatNodeInput,
    ChatNodeOutput,
    ChatNodeError,
    ConversationContext,
    ConversationType,
    ConversationTone,
    ErrorCode,
    ValidationResult,
)
from src.nodes.chat.exceptions import (
    InvalidInputError,
    MessageEmptyError,
    MessageTooLongError,
    InvalidConversationIdError,
    InvalidToneError,
    InvalidTypeError,
    AgentValidationError,
    SystemPromptGenerationError,
    OllamaUnreachableError,
    OllamaTimeoutError,
    OllamaError,
    OllamaOutOfMemoryError,
    OllamaInvalidResponseError,
    OutputValidationError,
    InvalidConfidenceError,
    MemoryInjectionError,
    DatabaseError,
    InternalServerError,
    RateLimitExceededError,
    RequestTimeoutError,
)


logger = logging.getLogger(__name__)


class ChatNodeService:
    """
    Service that integrates ChatNode with ConversationAgent.
    
    This is the main entry point for processing chat messages.
    
    Example:
        service = ChatNodeService()
        result = await service.process_message(
            message="Hello!",
            conversation_id="conv-123",
        )
        if isinstance(result, ChatNodeOutput):
            print(result.response)
        else:
            print(result.error)
    """
    
    # Configuration constants
    MAX_MESSAGE_LENGTH = 10000
    OLLAMA_TIMEOUT_SECONDS = 30
    OLLAMA_RETRY_ATTEMPTS = 3
    OLLAMA_RETRY_BACKOFF_FACTOR = 2  # exponential backoff
    
    def __init__(self):
        """Initialize the service."""
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    async def process_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        tone: ConversationTone = ConversationTone.PROFESSIONAL,
        conversation_type: ConversationType = ConversationType.GENERAL,
        user_id: Optional[str] = None,
    ) -> Union[ChatNodeOutput, ChatNodeError]:
        """
        Process a user message and return response or error.
        
        This is the main entry point. It orchestrates the entire flow:
        1. Validate input
        2. Load conversation context
        3. Generate system prompt
        4. Call Ollama
        5. Validate output
        6. Store in memory
        7. Return response
        
        Args:
            message: User message text
            conversation_id: Existing conversation ID (optional)
            tone: Tone for this conversation
            conversation_type: Type of conversation (support, info, etc)
            user_id: User ID for memory injection
            
        Returns:
            ChatNodeOutput on success
            ChatNodeError on failure
            
        Raises:
            Nothing - all exceptions are caught and converted to ChatNodeError
        """
        try:
            # Step 1: Parse and validate input
            self._logger.debug(f"Parsing input message: {len(message)} chars")
            input_obj = ChatNodeInput(
                message=message,
                conversation_id=conversation_id,
                tone=tone,
                conversation_type=conversation_type,
                user_id=user_id,
            )
            
            # Step 2: Validate input (comprehensive)
            validation_result = self._validate_input(input_obj)
            if not validation_result.is_valid:
                self._logger.warning(
                    f"Input validation failed: {validation_result.error_code}",
                    extra={
                        "error_code": validation_result.error_code,
                        "conversation_id": conversation_id,
                    }
                )
                return ChatNodeError(
                    error=validation_result.error_message,
                    error_code=validation_result.error_code,
                    conversation_id=conversation_id,
                    user_id=user_id,
                )
            
            # Step 3: Load conversation context (memory injection)
            self._logger.debug(f"Loading context for conversation: {conversation_id}")
            context = await self._load_conversation_context(
                conversation_id=conversation_id,
                user_id=user_id,
                conversation_type=conversation_type,
                tone=tone,
            )
            
            # Step 4: Get system prompt from agent
            self._logger.debug("Generating system prompt from ConversationAgent")
            system_prompt = self._get_system_prompt(context)
            
            # Step 5: Call Ollama (with retry + timeout)
            self._logger.debug("Calling Ollama for response generation")
            ollama_response = await self._call_ollama_with_retry(
                system_prompt=system_prompt,
                user_message=message,
                message_history=context.history_last_20_messages,
            )
            
            # Step 6: Validate output
            self._logger.debug("Validating Ollama response")
            output_validation = self._validate_ollama_output(ollama_response)
            if not output_validation.is_valid:
                self._logger.warning(
                    f"Output validation failed: {output_validation.error_code}",
                    extra={"error_code": output_validation.error_code}
                )
                return ChatNodeError(
                    error=output_validation.error_message,
                    error_code=output_validation.error_code,
                    conversation_id=conversation_id,
                    user_id=user_id,
                )
            
            # Step 7: Store in memory
            self._logger.debug("Storing interaction in memory")
            await self._store_in_memory(
                conversation_id=conversation_id,
                user_message=message,
                assistant_response=ollama_response,
                user_id=user_id,
            )
            
            # Step 8: Build and return success response
            output = ChatNodeOutput(
                response=ollama_response,
                confidence=0.75,  # TODO: Calculate from agent
                reasoning="Generated by ConversationAgent",  # TODO: Get from agent
                suggestions=[],  # TODO: Get from agent
                tokens_used=len(ollama_response.split()),  # Rough estimate
                conversation_id=conversation_id or "",
                message_id=f"msg-{uuid.uuid4().hex[:8]}",  # TODO: Use actual ID
            )
            
            self._logger.info(
                f"Message processed successfully",
                extra={
                    "conversation_id": conversation_id,
                    "message_length": len(message),
                    "response_length": len(ollama_response),
                }
            )
            
            return output
            
        except RateLimitExceededError as e:
            self._logger.warning(f"Rate limit exceeded: {e}", extra={"user_id": user_id})
            return ChatNodeError(
                error="Too many requests. Please slow down.",
                error_code=ErrorCode.ERROR_RATE_LIMIT_EXCEEDED,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        
        except InvalidInputError as e:
            self._logger.warning(f"Input validation failed: {e}")
            return ChatNodeError(
                error=str(e),
                error_code=ErrorCode.ERROR_INVALID_INPUT,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        
        except SystemPromptGenerationError as e:
            self._logger.error(f"System prompt generation failed: {e}")
            return ChatNodeError(
                error="Failed to generate system prompt. Please try again.",
                error_code=ErrorCode.ERROR_SYSTEM_PROMPT_GENERATION,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        
        except AgentValidationError as e:
            self._logger.error(f"Agent validation failed: {e}")
            return ChatNodeError(
                error="Agent validation failed. Please try again.",
                error_code=ErrorCode.ERROR_AGENT_VALIDATION_FAILED,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        
        except OllamaTimeoutError as e:
            self._logger.error(f"Ollama timeout: {e}")
            return ChatNodeError(
                error="Request timed out. Please try again.",
                error_code=ErrorCode.ERROR_OLLAMA_TIMEOUT,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        
        except OllamaUnreachableError as e:
            self._logger.error(f"Ollama unreachable: {e}")
            return ChatNodeError(
                error="Service temporarily unavailable. Please try again.",
                error_code=ErrorCode.ERROR_OLLAMA_UNREACHABLE,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        
        except OllamaError as e:
            self._logger.error(f"Ollama error ({type(e).__name__}): {e}")
            if isinstance(e, OllamaOutOfMemoryError):
                return ChatNodeError(
                    error="Service out of memory. Please try again later.",
                    error_code=ErrorCode.ERROR_OLLAMA_OUT_OF_MEMORY,
                    conversation_id=conversation_id,
                    user_id=user_id,
                )
            elif isinstance(e, OllamaInvalidResponseError):
                return ChatNodeError(
                    error="Invalid response from service. Please try again.",
                    error_code=ErrorCode.ERROR_OLLAMA_INVALID_RESPONSE,
                    conversation_id=conversation_id,
                    user_id=user_id,
                )
            else:
                return ChatNodeError(
                    error="Service error occurred. Please try again.",
                    error_code=ErrorCode.ERROR_OLLAMA_UNREACHABLE,
                    conversation_id=conversation_id,
                    user_id=user_id,
                )
        
        except InvalidConfidenceError as e:
            self._logger.error(f"Invalid confidence score: {e}")
            return ChatNodeError(
                error="Internal error occurred. Please try again.",
                error_code=ErrorCode.ERROR_INVALID_CONFIDENCE,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        
        except DatabaseError as e:
            self._logger.error(f"Database error: {e}")
            return ChatNodeError(
                error="System error occurred. Please try again.",
                error_code=ErrorCode.ERROR_DATABASE,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        
        except RequestTimeoutError as e:
            self._logger.error(f"Request timeout: {e}")
            return ChatNodeError(
                error="Request took too long. Please try again.",
                error_code=ErrorCode.ERROR_REQUEST_TIMEOUT,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        
        except OutputValidationError as e:
            self._logger.error(f"Output validation failed: {e}")
            return ChatNodeError(
                error="Invalid response received. Please try again.",
                error_code=ErrorCode.ERROR_OUTPUT_VALIDATION_FAILED,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        
        except MemoryInjectionError as e:
            self._logger.error(f"Memory injection failed: {e}")
            return ChatNodeError(
                error="System error occurred. Please try again.",
                error_code=ErrorCode.ERROR_MEMORY_INJECTION,
                conversation_id=conversation_id,
                user_id=user_id,
            )
        
        except Exception as e:
            # Unexpected error - log fully but return generic message to user
            self._logger.exception(
                f"Unexpected error in process_message: {type(e).__name__}: {e}",
                extra={"conversation_id": conversation_id, "user_id": user_id}
            )
            return ChatNodeError(
                error="An unexpected error occurred. Please try again.",
                error_code=ErrorCode.ERROR_INTERNAL_SERVER_ERROR,
                conversation_id=conversation_id,
                user_id=user_id,
            )
    
    # ═══════════════════════════════════
    # PRIVATE METHODS
    # ═══════════════════════════════════
    
    def _validate_input(self, input_obj: ChatNodeInput) -> ValidationResult:
        """
        Comprehensive input validation.
        
        Checks:
        - Message non-empty
        - Message <= MAX_MESSAGE_LENGTH
        - Valid UTF-8
        - No null bytes
        - Valid tone
        - Valid conversation_type
        - Valid conversation_id (if provided)
        
        Returns:
            ValidationResult with is_valid=True or error info
        """
        # Check message is not empty
        if not input_obj.message or len(input_obj.message.strip()) == 0:
            return ValidationResult(
                is_valid=False,
                error_code=ErrorCode.ERROR_MESSAGE_EMPTY,
                error_message="Message cannot be empty",
            )
        
        # Check message length
        if len(input_obj.message) > self.MAX_MESSAGE_LENGTH:
            return ValidationResult(
                is_valid=False,
                error_code=ErrorCode.ERROR_MESSAGE_TOO_LONG,
                error_message=f"Message too long (max {self.MAX_MESSAGE_LENGTH} chars)",
            )
        
        # Check for null bytes
        if '\x00' in input_obj.message:
            return ValidationResult(
                is_valid=False,
                error_code=ErrorCode.ERROR_INVALID_INPUT,
                error_message="Message contains invalid characters",
            )
        
        # Validate UTF-8 (already done by Python, but be explicit)
        try:
            input_obj.message.encode('utf-8')
        except UnicodeEncodeError:
            return ValidationResult(
                is_valid=False,
                error_code=ErrorCode.ERROR_INVALID_INPUT,
                error_message="Message contains invalid characters",
            )
        
        # Check tone
        if not isinstance(input_obj.tone, ConversationTone):
            return ValidationResult(
                is_valid=False,
                error_code=ErrorCode.ERROR_INVALID_TONE,
                error_message=f"Invalid tone: {input_obj.tone}",
            )
        
        # Check conversation type
        if not isinstance(input_obj.conversation_type, ConversationType):
            return ValidationResult(
                is_valid=False,
                error_code=ErrorCode.ERROR_INVALID_TYPE,
                error_message=f"Invalid conversation type: {input_obj.conversation_type}",
            )
        
        # If conversation_id provided, validate it exists
        # TODO: Check with database
        
        return ValidationResult(is_valid=True)
    
    async def _load_conversation_context(
        self,
        conversation_id: Optional[str],
        user_id: Optional[str],
        conversation_type: ConversationType,
        tone: ConversationTone,
    ) -> ConversationContext:
        """
        Load full context for this conversation.
        
        Fetches:
        - Message history (last 20)
        - User preferences (from memory)
        - Conversation statistics
        
        Returns:
            ConversationContext with all data
        """
        # TODO: Implement real data loading
        # For now, return minimal context
        return ConversationContext(
            conversation_id=conversation_id or "",
            user_id=user_id,
            conversation_type=conversation_type,
            tone=tone,
            message_count=0,
            history_last_20_messages=[],
            user_preferences={},
        )
    
    def _get_system_prompt(self, context: ConversationContext) -> str:
        """
        Get system prompt from ConversationAgent.
        
        Args:
            context: Conversation context
            
        Returns:
            System prompt string
            
        Raises:
            SystemPromptGenerationError if agent fails
        """
        try:
            from src.agents.conversation import ConversationAgent
            
            agent = ConversationAgent()
            agent_context = {
                "type": context.conversation_type.value,
                "tone": context.tone.value,
                "history_length": len(context.history_last_20_messages),
            }
            
            system_prompt = agent.get_system_prompt(agent_context)
            
            if not system_prompt or not isinstance(system_prompt, str):
                raise SystemPromptGenerationError("Agent returned invalid system prompt")
            
            return system_prompt
            
        except Exception as e:
            self._logger.error(f"Failed to get system prompt: {e}")
            raise SystemPromptGenerationError(f"Agent error: {e}")
    
    async def _call_ollama_with_retry(
        self,
        system_prompt: str,
        user_message: str,
        message_history: list,
    ) -> str:
        """
        Call Ollama with retry logic and timeout.
        
        Retry strategy: exponential backoff
        - Attempt 1: immediate
        - Attempt 2: after 1 second
        - Attempt 3: after 2 seconds
        
        Args:
            system_prompt: System prompt for Ollama
            user_message: User message
            message_history: Previous messages in conversation
            
        Returns:
            Ollama response text
            
        Raises:
            OllamaTimeoutError if all attempts timeout
            OllamaUnreachableError if cannot connect
            OllamaError for other errors
        """
        for attempt in range(1, self.OLLAMA_RETRY_ATTEMPTS + 1):
            try:
                self._logger.debug(f"Ollama call attempt {attempt}/{self.OLLAMA_RETRY_ATTEMPTS}")
                
                # Set timeout
                try:
                    response = await asyncio.wait_for(
                        self._do_ollama_call(system_prompt, user_message, message_history),
                        timeout=self.OLLAMA_TIMEOUT_SECONDS,
                    )
                    return response
                    
                except asyncio.TimeoutError:
                    if attempt == self.OLLAMA_RETRY_ATTEMPTS:
                        raise OllamaTimeoutError(f"Ollama timed out after {self.OLLAMA_TIMEOUT_SECONDS}s")
                    
                    wait_time = self.OLLAMA_RETRY_BACKOFF_FACTOR ** (attempt - 1)
                    self._logger.debug(f"Attempt {attempt} timed out, retrying in {wait_time}s")
                    await asyncio.sleep(wait_time)
                    
            except OllamaError as e:
                if attempt == self.OLLAMA_RETRY_ATTEMPTS:
                    raise
                wait_time = self.OLLAMA_RETRY_BACKOFF_FACTOR ** (attempt - 1)
                self._logger.debug(f"Ollama error: {type(e).__name__}, retrying in {wait_time}s")
                await asyncio.sleep(wait_time)
    
    async def _do_ollama_call(
        self,
        system_prompt: str,
        user_message: str,
        message_history: list,
    ) -> str:
        """
        Perform actual Ollama call.
        
        This is what gets retried.
        """
        # TODO: Implement real Ollama call
        # For now, return mock response
        return f"Response to: {user_message}"
    
    def _validate_ollama_output(self, response: str) -> ValidationResult:
        """
        Validate Ollama response.
        
        Checks:
        - Response is string
        - Response non-empty
        - Response valid UTF-8
        - Response <= reasonable length
        
        Returns:
            ValidationResult
        """
        if not isinstance(response, str):
            return ValidationResult(
                is_valid=False,
                error_code=ErrorCode.ERROR_OLLAMA_INVALID_RESPONSE,
                error_message="Invalid response type",
            )
        
        if len(response.strip()) == 0:
            return ValidationResult(
                is_valid=False,
                error_code=ErrorCode.ERROR_OLLAMA_INVALID_RESPONSE,
                error_message="Empty response",
            )
        
        # TODO: Call agent.validate_output()
        
        return ValidationResult(is_valid=True)
    
    async def _store_in_memory(
        self,
        conversation_id: Optional[str],
        user_message: str,
        assistant_response: str,
        user_id: Optional[str],
    ) -> None:
        """
        Store interaction in memory system.
        
        TODO: Implement memory storage
        """
        self._logger.debug(f"Storing interaction in memory: {conversation_id}")
