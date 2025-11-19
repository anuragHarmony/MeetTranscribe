"""
Base interface for LLM integration
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from ..transcription.base import TranscriptionResult


@dataclass
class SummaryResult:
    """
    AI-generated meeting summary
    """
    summary: str
    key_points: List[str]
    action_items: List[str]
    decisions: List[str]
    questions: List[str]
    topics: List[str]
    sentiment: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LLMInterface(ABC):
    """
    Interface for LLM-based meeting analysis
    """

    @abstractmethod
    def generate_summary(
        self,
        transcription: TranscriptionResult,
        include_action_items: bool = True,
        include_sentiment: bool = False
    ) -> SummaryResult:
        """
        Generate comprehensive meeting summary

        Args:
            transcription: Meeting transcription
            include_action_items: Extract action items
            include_sentiment: Perform sentiment analysis

        Returns:
            SummaryResult: AI-generated summary and insights
        """
        pass

    @abstractmethod
    def answer_question(
        self,
        transcription: TranscriptionResult,
        question: str
    ) -> str:
        """
        Answer a question about the meeting

        Args:
            transcription: Meeting transcription
            question: User question

        Returns:
            str: Answer to the question
        """
        pass

    @abstractmethod
    def extract_topics(
        self,
        transcription: TranscriptionResult
    ) -> List[str]:
        """
        Extract main topics discussed

        Args:
            transcription: Meeting transcription

        Returns:
            List[str]: List of topics
        """
        pass
