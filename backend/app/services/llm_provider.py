from __future__ import annotations
"""
LLM Provider Abstraction.

Design goal: Provider-agnostic interface for language tasks.
Only used for intent parsing and explanation verbalization.
NEVER for planning, scoring, or execution.

Includes a rule-based fallback so the app works without any API key.
"""
import re
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


# ═══════════════════════════════════════════════════════════════════════════════
# RULE-BASED FALLBACK (works without any API key)
# ═══════════════════════════════════════════════════════════════════════════════

class RuleBasedProvider(LLMProvider):
    """Simple keyword-based intent parser. No API key needed."""

    # Keywords that signal activity type
    DEEP_WORK_KEYWORDS = [
        "write", "code", "coding", "program", "design", "research",
        "study", "focus", "deep work", "think", "analyze", "build",
        "develop", "implement", "architect", "plan project",
    ]
    MEETING_KEYWORDS = [
        "meeting", "meet", "call", "sync", "standup", "stand-up",
        "1:1", "one-on-one", "interview", "presentation", "demo",
    ]
    BREAK_KEYWORDS = [
        "break", "rest", "nap", "walk", "lunch", "coffee", "relax",
        "stretch", "meditate", "meditation",
    ]
    ADMIN_KEYWORDS = [
        "email", "emails", "inbox", "slack", "respond", "reply",
        "review", "approve", "expenses", "admin", "paperwork",
    ]
    PERSONAL_KEYWORDS = [
        "gym", "exercise", "workout", "doctor", "dentist", "pickup",
        "errands", "grocery", "shopping", "appointment", "personal",
    ]

    # Time patterns
    TIME_PATTERNS = [
        (r'\b(\d{1,2})\s*(am|pm)\b', None),  # "3pm", "10am"
        (r'\bmorning\b', 'morning'),
        (r'\bafternoon\b', 'afternoon'),
        (r'\bevening\b', 'evening'),
        (r'\btonight\b', 'evening'),
    ]

    # Duration patterns
    DURATION_PATTERNS = [
        (r'(\d+)\s*(?:hours?|hrs?|h)\b', lambda m: int(m.group(1)) * 60),
        (r'(\d+)\s*(?:minutes?|mins?|min|m)\b', lambda m: int(m.group(1))),
        (r'half\s*(?:an?\s*)?hour', lambda m: 30),
        (r'(?:an?\s*)?hour\s*(?:and\s*(?:a\s*)?half)?', lambda m: 90),
        (r'(?:an?\s*)?hour', lambda m: 60),
    ]

    # Participant patterns
    PARTICIPANT_PATTERNS = [
        r'with\s+(\w+(?:\s+\w+)?)',
        r'(?:and|,)\s+(\w+)\s+(?:meeting|call|sync)',
    ]

    def _detect_activity(self, text: str) -> tuple[str, str]:
        """Detect activity nature and energy level from text."""
        lower = text.lower()

        for kw in self.MEETING_KEYWORDS:
            if kw in lower:
                return "MEETING", "MEDIUM"

        for kw in self.DEEP_WORK_KEYWORDS:
            if kw in lower:
                return "DEEP_WORK", "HIGH"

        for kw in self.BREAK_KEYWORDS:
            if kw in lower:
                return "BREAK", "LOW"

        for kw in self.ADMIN_KEYWORDS:
            if kw in lower:
                return "ADMIN", "LOW"

        for kw in self.PERSONAL_KEYWORDS:
            if kw in lower:
                return "PERSONAL", "MEDIUM"

        return "SHALLOW_WORK", "MEDIUM"

    def _detect_duration(self, text: str) -> int | None:
        """Extract duration in minutes from text."""
        lower = text.lower()
        for pattern, extractor in self.DURATION_PATTERNS:
            match = re.search(pattern, lower)
            if match:
                return extractor(match)
        return None

    def _detect_time_preference(self, text: str) -> str | None:
        """Extract time preference from text."""
        lower = text.lower()
        for pattern, label in self.TIME_PATTERNS:
            match = re.search(pattern, lower)
            if match:
                if label:
                    return label
                # Parse specific time
                hour = int(match.group(1))
                ampm = match.group(2)
                if ampm == "pm" and hour != 12:
                    hour += 12
                if hour < 12:
                    return "morning"
                elif hour < 17:
                    return "afternoon"
                else:
                    return "evening"
        return None

    def _detect_participants(self, text: str) -> list[str]:
        """Extract participant names from text."""
        participants = []
        lower = text.lower()
        for pattern in self.PARTICIPANT_PATTERNS:
            match = re.search(pattern, lower)
            if match:
                name = match.group(1).strip()
                # Filter out common non-name words
                skip = {"the", "a", "an", "my", "some", "team", "me"}
                if name not in skip:
                    participants.append(name)
        return participants

    async def parse_intent(self, user_input: str) -> ParsedIntent:
        """Parse user input using keyword rules."""
        activity, energy = self._detect_activity(user_input)
        duration = self._detect_duration(user_input)
        time_pref = self._detect_time_preference(user_input)
        participants = self._detect_participants(user_input)

        # Use the raw input as the goal, cleaned up
        goal = user_input.strip()
        if len(goal) > 100:
            goal = goal[:97] + "..."

        return ParsedIntent(
            goal=goal,
            participants=participants,
            duration_minutes=duration,
            time_preference=time_pref,
            activity_nature=activity,
            energy_level_required=energy,
            confidence=0.7,
        )

    async def verbalize_explanation(self, facts: dict) -> str:
        """Generate explanation from facts using templates."""
        reasons = facts.get("reasons", [])
        avoided = facts.get("avoided", [])

        parts = []
        reason_map = {
            "good_energy_alignment": "This slot aligns well with your energy levels",
            "morning_focus_window": "Scheduled during your morning focus window",
            "afternoon_energy_peak": "Placed in the afternoon when energy naturally peaks",
            "available_slot": "Found a good open slot in your schedule",
        }
        for r in reasons:
            if r in reason_map:
                parts.append(reason_map[r])
                break

        if not parts:
            parts.append("Scheduled based on your available time")

        avoid_map = {
            "cognitive_overload": "while keeping your cognitive load manageable",
            "back_to_back_deep_work": "with buffer time to avoid back-to-back intense work",
        }
        for a in avoided:
            if a in avoid_map:
                parts.append(avoid_map[a])
                break

        return ". ".join(parts) + "."


# ═══════════════════════════════════════════════════════════════════════════════
# OPENAI PROVIDER
# ═══════════════════════════════════════════════════════════════════════════════

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
            # Fallback to template
            print(f"LLM verbalize error: {e}")
            return "Scheduled based on your current energy levels and available time."


# ═══════════════════════════════════════════════════════════════════════════════
# FACTORY
# ═══════════════════════════════════════════════════════════════════════════════

def get_llm_provider() -> LLMProvider:
    """Factory for getting the configured LLM provider.

    Falls back to rule-based provider if no API key is configured.
    """
    if not settings.llm_api_key:
        return RuleBasedProvider()

    if settings.llm_provider == "openai":
        return OpenAIProvider()

    # Unknown provider but has API key - try OpenAI as default
    return OpenAIProvider()
