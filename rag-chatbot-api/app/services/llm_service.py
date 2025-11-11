"""
LLM service for interacting with OpenAI API.
Handles chat completions, streaming, and token management.
"""
from typing import AsyncIterator, Dict, List, Optional

from openai import AsyncOpenAI, OpenAIError

from app.config import settings
from app.core.exceptions import LLMError
from app.utils.logging import get_logger

logger = get_logger(__name__)


class LLMService:
    """Service for LLM interactions."""

    def __init__(self, api_key: str = None, model: str = None):
        """
        Initialize LLM service.

        Args:
            api_key: OpenAI API key (optional, uses settings by default)
            model: Model name (optional, uses settings by default)
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model or settings.OPENAI_MODEL
        self.client = AsyncOpenAI(api_key=self.api_key)

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> Dict:
        """
        Generate a response from the LLM.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (optional)
            max_tokens: Maximum tokens to generate (optional)
            **kwargs: Additional arguments for the API

        Returns:
            Dictionary with response and metadata

        Raises:
            LLMError: If generation fails
        """
        try:
            temperature = temperature if temperature is not None else settings.OPENAI_TEMPERATURE
            max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS

            logger.info(
                "llm_request_starting",
                model=self.model,
                messages_count=len(messages),
                max_tokens=max_tokens
            )

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            result = {
                "content": response.choices[0].message.content,
                "model": response.model,
                "tokens_used": {
                    "prompt": response.usage.prompt_tokens,
                    "completion": response.usage.completion_tokens,
                    "total": response.usage.total_tokens
                },
                "finish_reason": response.choices[0].finish_reason
            }

            logger.info(
                "llm_response_received",
                model=response.model,
                tokens=result["tokens_used"]["total"],
                finish_reason=result["finish_reason"]
            )

            return result

        except OpenAIError as e:
            logger.error("llm_request_failed", error=str(e))
            raise LLMError(f"LLM request failed: {str(e)}")

        except Exception as e:
            logger.error("llm_unexpected_error", error=str(e))
            raise LLMError(f"Unexpected error in LLM service: {str(e)}")

    async def generate_response_stream(
        self,
        messages: List[Dict[str, str]],
        temperature: float = None,
        max_tokens: int = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Generate a streaming response from the LLM.

        Args:
            messages: List of message dictionaries
            temperature: Sampling temperature (optional)
            max_tokens: Maximum tokens to generate (optional)
            **kwargs: Additional arguments for the API

        Yields:
            Response chunks as strings

        Raises:
            LLMError: If generation fails
        """
        try:
            temperature = temperature if temperature is not None else settings.OPENAI_TEMPERATURE
            max_tokens = max_tokens or settings.OPENAI_MAX_TOKENS

            logger.info(
                "llm_streaming_request_starting",
                model=self.model,
                messages_count=len(messages)
            )

            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

            logger.info("llm_streaming_complete")

        except OpenAIError as e:
            logger.error("llm_streaming_failed", error=str(e))
            raise LLMError(f"LLM streaming request failed: {str(e)}")

        except Exception as e:
            logger.error("llm_streaming_unexpected_error", error=str(e))
            raise LLMError(f"Unexpected error in LLM streaming: {str(e)}")

    async def create_prompt(
        self,
        system_message: str,
        user_message: str,
        context: Optional[str] = None,
        chat_history: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        Create a properly formatted prompt with context and history.

        Args:
            system_message: System instruction
            user_message: User's message
            context: Optional context from RAG
            chat_history: Optional previous messages

        Returns:
            List of message dictionaries
        """
        messages = []

        # Add system message
        if context:
            system_with_context = f"{system_message}\n\nContext:\n{context}"
            messages.append({"role": "system", "content": system_with_context})
        else:
            messages.append({"role": "system", "content": system_message})

        # Add chat history
        if chat_history:
            messages.extend(chat_history)

        # Add current user message
        messages.append({"role": "user", "content": user_message})

        return messages

    async def count_tokens(self, text: str) -> int:
        """
        Count tokens in a text string.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        try:
            import tiktoken

            encoding = tiktoken.encoding_for_model(self.model)
            return len(encoding.encode(text))

        except Exception as e:
            logger.warning("token_counting_failed", error=str(e))
            # Fallback: rough estimate (1 token ≈ 4 characters)
            return len(text) // 4

    async def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """
        Estimate the cost of a request.

        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens

        Returns:
            Estimated cost in USD
        """
        # GPT-4 Turbo pricing (as of 2024)
        # These are example prices - update with actual pricing
        pricing = {
            "gpt-4-turbo-preview": {
                "prompt": 0.01 / 1000,    # $0.01 per 1K tokens
                "completion": 0.03 / 1000  # $0.03 per 1K tokens
            },
            "gpt-4": {
                "prompt": 0.03 / 1000,
                "completion": 0.06 / 1000
            },
            "gpt-3.5-turbo": {
                "prompt": 0.0005 / 1000,
                "completion": 0.0015 / 1000
            }
        }

        model_pricing = pricing.get(self.model, pricing["gpt-4-turbo-preview"])

        cost = (
            prompt_tokens * model_pricing["prompt"] +
            completion_tokens * model_pricing["completion"]
        )

        return round(cost, 6)
