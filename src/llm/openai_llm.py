"""
OpenAI GPT integration for meeting summaries
"""

from typing import List
import json
from .base import LLMInterface, SummaryResult
from ..transcription.base import TranscriptionResult

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class OpenAILLM(LLMInterface):
    """
    OpenAI GPT-4 integration for meeting analysis

    Provides best-in-class summaries and insights
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4-turbo-preview",
        temperature: float = 0.3
    ):
        """
        Initialize OpenAI LLM

        Args:
            api_key: OpenAI API key
            model: Model name (gpt-4-turbo-preview, gpt-4, gpt-3.5-turbo)
            temperature: Sampling temperature (0.0-1.0)
        """
        if OpenAI is None:
            raise ImportError(
                "openai is not installed. "
                "Install it with: pip install openai"
            )

        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.temperature = temperature

    def generate_summary(
        self,
        transcription: TranscriptionResult,
        include_action_items: bool = True,
        include_sentiment: bool = False
    ) -> SummaryResult:
        """
        Generate comprehensive meeting summary using GPT-4

        Args:
            transcription: Meeting transcription
            include_action_items: Extract action items
            include_sentiment: Perform sentiment analysis

        Returns:
            SummaryResult: AI-generated summary
        """
        # Build prompt
        prompt = self._build_summary_prompt(
            transcription,
            include_action_items,
            include_sentiment
        )

        # Call OpenAI API
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are an expert meeting analyst. Provide clear, actionable summaries."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=self.temperature,
            response_format={"type": "json_object"}
        )

        # Parse response
        result_json = json.loads(response.choices[0].message.content)

        return SummaryResult(
            summary=result_json.get("summary", ""),
            key_points=result_json.get("key_points", []),
            action_items=result_json.get("action_items", []),
            decisions=result_json.get("decisions", []),
            questions=result_json.get("questions", []),
            topics=result_json.get("topics", []),
            sentiment=result_json.get("sentiment") if include_sentiment else None,
            metadata={"model": self.model}
        )

    def _build_summary_prompt(
        self,
        transcription: TranscriptionResult,
        include_action_items: bool,
        include_sentiment: bool
    ) -> str:
        """Build prompt for meeting summary"""
        # Format transcript with speakers
        transcript_text = []
        for segment in transcription.segments:
            speaker = segment.speaker or "Unknown"
            transcript_text.append(f"{speaker}: {segment.text}")

        transcript = "\n".join(transcript_text)

        prompt = f"""Analyze this meeting transcript and provide a comprehensive summary.

TRANSCRIPT:
{transcript}

Please provide a JSON response with the following structure:
{{
    "summary": "A concise 2-3 sentence overview of the meeting",
    "key_points": ["List of main points discussed"],
    "topics": ["Main topics covered"],
"""

        if include_action_items:
            prompt += """    "action_items": ["Specific actions to be taken"],
    "decisions": ["Decisions made during the meeting"],
    "questions": ["Unresolved questions or topics for follow-up"],
"""

        if include_sentiment:
            prompt += """    "sentiment": "Overall sentiment (positive/neutral/negative)",
"""

        prompt += """}

Be specific and actionable. Focus on outcomes and next steps."""

        return prompt

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
            str: Answer
        """
        # Format transcript
        transcript_text = []
        for segment in transcription.segments:
            speaker = segment.speaker or "Unknown"
            transcript_text.append(f"{speaker}: {segment.text}")

        transcript = "\n".join(transcript_text)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": "You are a helpful assistant that answers questions about meeting transcripts."
                },
                {
                    "role": "user",
                    "content": f"""Based on this meeting transcript, please answer the following question:

TRANSCRIPT:
{transcript}

QUESTION: {question}

Please provide a clear, concise answer based only on information in the transcript."""
                }
            ],
            temperature=self.temperature
        )

        return response.choices[0].message.content

    def extract_topics(
        self,
        transcription: TranscriptionResult
    ) -> List[str]:
        """
        Extract main topics discussed

        Args:
            transcription: Meeting transcription

        Returns:
            List[str]: Topics
        """
        summary = self.generate_summary(transcription, include_action_items=False)
        return summary.topics
