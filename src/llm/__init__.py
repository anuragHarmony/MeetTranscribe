"""
LLM integration for AI-powered meeting summaries and insights
"""

from .base import LLMInterface, SummaryResult
from .openai_llm import OpenAILLM
from .anthropic_llm import AnthropicLLM
from .local_llm import LocalLLM

__all__ = [
    "LLMInterface",
    "SummaryResult",
    "OpenAILLM",
    "AnthropicLLM",
    "LocalLLM"
]
