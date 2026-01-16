from __future__ import annotations
"""
LLM Provider Abstraction.

Design goal: Provider-agnostic interface for language tasks.
Only used for intent parsing and explanation verbalization.
NEVER for planning, scoring, or execution.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass

import httpx

from app.core.config import settings


@dataclass
class ParsedIntent:
    """Structured output from LLM intent parsing."""
    goal: str
    participants: list[str]
    duration_minutes: int | None
    time_preference: str | None
    activity_nature: str
    energy_level_required: str
    confidence: float


class LLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def parse_intent(self, user_input: str) -> ParsedIntent:
        """Parse natural language into structured intent."""
        pass

    @abstractmethod
    async def verbalize_explanation(self, facts: dict) -> str:
        """Turn structured explanation facts into natural prose."""
        pass


class OpenAIProvider(LLMProvider):
    """OpenAI implementation of LLM provider."""

    PARSE_SYSTEM_PROMPT = """You are parsing a scheduling request.
Extract structured information about what the user wants to schedule.
Be conservative with confidence - if something is ambiguous, mark it as null.
Do not invent information not explicitly stated in the input."""

    PARSE_SCHEMA = {
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "What the user wants to accomplish"},
            "participants": {
                "type": "array",
                "items": {"type": "string"},
                "description": "People involved (empty if solo)",
            },
            "duration_minutes": {
                "type": ["integer", "null"],
                "description": "Duration in minutes if specified",
            },
            "time_preference": {
                "type": ["string", "null"],
                "description": "When they want to do it (morning/afternoon/evening/specific time)",
            },
            "activity_nature": {
                "type": "string",
                "enum": ["DEEP_WORK", "SHALLOW_WORK", "MEETING", "BREAK", "PERSONAL", "ADMIN"],
            },
            "energy_level_required": {
                "type": "string",
                "enum": ["LOW", "MEDIUM", "HIGH"],
            },
            "confidence": {
                "type": "number",
                "description": "Your confidence in this parsing (0.0-1.0)",
            },
        },
        "required": ["goal", "activity_nature", "energy_level_required", "confidence"],
    }

    async def parse_intent(self, user_input: str) -> ParsedIntent:
        """Parse natural language using OpenAI."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "messages": [
                        {"role": "system", "content": self.PARSE_SYSTEM_PROMPT},
                        {"role": "user", "content": user_input},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": "parsed_intent",
                            "schema": self.PARSE_SCHEMA,
                        },
                    },
                },
                timeout=30.0,
            )
            response.raise_for_status()
            data = response.json()

        import json
        parsed = json.loads(data["choices"][0]["message"]["content"])

        return ParsedIntent(
            goal=parsed["goal"],
            participants=parsed.get("participants", []),
            duration_minutes=parsed.get("duration_minutes"),
            time_preference=parsed.get("time_preference"),
            activity_nature=parsed["activity_nature"],
            energy_level_required=parsed["energy_level_required"],
            confidence=parsed["confidence"],
        )

    async def verbalize_explanation(self, facts: dict) -> str:
        """Turn structured facts into natural language."""
        prompt = f"""Turn these scheduling explanation facts into 1-2 friendly sentences.
Focus on why this timing works well for the user's energy and focus.
Do not use technical jargon. Keep it brief.

Facts: {facts}"""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {settings.llm_api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": settings.llm_model,
                        "messages": [{"role": "user", "content": prompt}],
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            return data["choices"][0]["message"]["content"].strip()
        except Exception as e:
            # Fallback to a simple template-based explanation
            print(f"LLM verbalize error: {e}")
            slot = facts.get("selected_slot", {})
            return f"Scheduled based on your current energy levels and available time."


def get_llm_provider() -> LLMProvider:
    """Factory for getting the configured LLM provider."""
    if settings.llm_provider == "openai":
        return OpenAIProvider()
    # Add more providers here as needed
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider}")
