"""Cloud LLM integration service for Hugging Face Inference Providers API."""
import aiohttp
import json
import logging
from datetime import datetime
from typing import AsyncIterator, Optional

from ..utils.config import settings
from ..utils.helpers import get_current_timestamp
from .llm import LLMResponse

logger = logging.getLogger(__name__)

class CloudLLMService:
    """Service for interacting with a cloud-hosted LLM via Hugging Face Inference API."""

    def __init__(self):
        self.api_url = settings.hf_api_url.rstrip('/')
        self.token = settings.hf_api_token
        self.default_model = settings.hf_default_model
        self.max_new_tokens = settings.lm_max_new_tokens or settings.lm_max_tokens  # reuse existing setting
        self.temperature = settings.lm_temperature
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        timeout = aiohttp.ClientTimeout(total=120)
        headers = {}
        if self.token:
            headers['Authorization'] = f"Bearer {self.token}"
        self.session = aiohttp.ClientSession(timeout=timeout, headers=headers)
        # Log cloud LLM config
        logger.info(
            f"Cloud LLM initialized with base_url={self.api_url}, model={self.default_model}, "
            f"max_new_tokens={self.max_new_tokens}, temperature={self.temperature}"
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def generate_response(
        self,
        prompt: str,
        model: Optional[str] = None
    ) -> LLMResponse:
        """Generate a non-streaming response from cloud LLM using OpenAI-compatible format."""
        if not self.session:
            raise RuntimeError("CloudLLMService not initialized. Use async context manager.")
        
        model_name = model or self.default_model
        url = f"{self.api_url}/chat/completions"
        
        # Convert to OpenAI chat completions format
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "stream": False
        }
        
        start = get_current_timestamp()
        async with self.session.post(url, json=payload) as resp:
            # Handle HTTP errors gracefully
            if resp.status != 200:
                err_text = await resp.text()
                logger.error(f"Cloud LLM request failed: {resp.status} - {err_text}")
                # Return as error content rather than exception
                return LLMResponse(
                    content=f"Error from Cloud LLM: {err_text}",
                    processing_time=(get_current_timestamp() - start).total_seconds()
                )
            
            data = await resp.json()
        elapsed = (get_current_timestamp() - start).total_seconds()
        
        # Extract content from OpenAI-compatible response format
        text = ''
        if isinstance(data, dict) and 'choices' in data and data['choices']:
            choice = data['choices'][0]
            if 'message' in choice and 'content' in choice['message']:
                text = choice['message']['content']
        
        return LLMResponse(content=text, processing_time=elapsed)

    async def generate_response_stream(
        self,
        prompt: str,
        model: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Generate a streaming response from cloud LLM using OpenAI-compatible format."""
        if not self.session:
            raise RuntimeError("CloudLLMService not initialized. Use async context manager.")
        
        model_name = model or self.default_model
        url = f"{self.api_url}/chat/completions"
        
        # Convert to OpenAI chat completions format with streaming
        payload = {
            "model": model_name,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": self.max_new_tokens,
            "temperature": self.temperature,
            "stream": True
        }
        
        logger.info(f"Cloud LLM streaming to {url}")
        
        async with self.session.post(url, json=payload) as resp:
            if resp.status == 404:
                # Model doesn't support streaming; fallback to full response
                logger.warning(f"Cloud LLM model {model_name} does not support streaming, falling back to non-stream.")
                result = await self.generate_response(prompt, model)
                yield result.content
                return
            
            if resp.status != 200:
                err_text = await resp.text()
                raise RuntimeError(f"Hugging Face API error {resp.status}: {err_text}")
            
            # Stream line-by-line for Server-Sent Events
            async for line in resp.content:
                chunk = line.decode('utf-8').strip()
                if not chunk or not chunk.startswith('data: '):
                    continue
                
                # Remove 'data: ' prefix
                data_str = chunk[6:]
                if data_str == '[DONE]':
                    break
                
                try:
                    data = json.loads(data_str)
                    if 'choices' in data and data['choices']:
                        choice = data['choices'][0]
                        if 'delta' in choice and 'content' in choice['delta']:
                            yield choice['delta']['content']
                except json.JSONDecodeError:
                    continue

# Global cloud LLM instance
cloud_llm_service = CloudLLMService()