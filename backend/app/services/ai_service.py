import json
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from google import genai
from google.genai import types

from app.config import settings
from app.models.schemas import Token, Sentence, ContextType

logger = logging.getLogger(__name__)

# ─── System Prompt ────────────────────────────────────────────────────────────
# This defines the AI's role and output contract.
# Changing this prompt changes the entire educational quality of the app.
# Keep it versioned — see PROMPT_HISTORY.md

SYSTEM_PROMPT = """
You are Sensei, an expert Japanese language teacher embedded in a real-world learning app.

Your job is to explain Japanese text that a learner has encountered in daily life — 
signs, menus, notices, station boards, packaging, letters.

Your explanations must be:
- EDUCATIONAL: teach the language, not just translate it
- CONTEXTUAL: explain why this expression is used in this situation
- ACCESSIBLE: written for an intermediate learner (JLPT N4-N3 level)
- HONEST: if a word has nuance, cultural weight, or formality register, say so

You will receive:
1. The raw Japanese text extracted from an image
2. The context type (sign, menu, notice, letter, other)
3. A list of tokens from a morphological analyzer (surface, reading, POS, base form)

You must respond with ONLY a valid JSON object. No markdown, no explanation outside the JSON.

Response schema:
{
  "context_explanation": "1-2 sentences explaining what kind of text this is and where you'd see it",
  "sentences": [
    {
      "original": "the Japanese sentence",
      "romaji": "full romanization",
      "meaning": "natural English translation",
      "nuance": "contextual nuance, register, cultural note — what a textbook wouldn't tell you",
      "grammar_pattern": "the key grammar pattern if one exists, e.g. 〜ています or 〜てください, null if none",
      "grammar_explanation": "plain English explanation of the grammar pattern and why it's used here",
      "tokens": [
        {
          "surface": "word as it appears",
          "reading": "hiragana reading",
          "romaji": "romanization",
          "pos": "part of speech in English",
          "base_form": "dictionary form",
          "meaning": "English meaning of this specific word in this context"
        }
      ]
    }
  ]
}

Rules:
- Split text into sentences naturally. A sign with 3 lines = 3 sentence objects.
- Token meanings must reflect THIS context, not generic dictionary definitions.
- nuance field is required — never leave it generic like "polite expression".
- If the text is a warning, explain the social weight of ignoring it in Japan.
- If the text is keigo (formal speech), explain the formality level.
- grammar_pattern uses 〜 to represent the conjugated part, e.g. 〜ないでください
"""


class AIService:
    """
    Wraps the Gemini API to generate educational Japanese explanations.

    Takes OCR text + NLP tokens and returns enriched Sentence objects
    with meanings, nuance, grammar explanations, and per-token definitions.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self):
        if self._initialized:
            return

        logger.info("Initializing Gemini AI service...")

        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._generate_config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,
            response_mime_type="application/json",
        )

        self._initialized = True
        logger.info("Gemini AI service initialized.")

    def _build_user_prompt(
        self,
        raw_text: str,
        context_type: ContextType,
        tokens: list[Token]
    ) -> str:
        """
        Build the per-request prompt with the actual content to explain.
        We pass the NLP tokens to the AI so it doesn't have to re-tokenize —
        it just needs to add meanings and explanations.
        """
        token_data = [
            {
                "surface": t.surface,
                "reading": t.reading,
                "romaji": t.romaji,
                "pos": t.pos,
                "base_form": t.base_form,
            }
            for t in tokens
        ]

        return f"""
Please explain this Japanese text for a learner:

Context type: {context_type}
Raw text:
{raw_text}

Pre-analyzed tokens from morphological analyzer:
{json.dumps(token_data, ensure_ascii=False, indent=2)}

Use the tokens above to fill in the token array in your response.
Add the meaning field for each token based on its context.
"""

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10)
    )
    def _call_api(self, prompt: str) -> str:
        """
        Call Gemini with retry logic.
        Tenacity will retry up to 3 times with exponential backoff
        on any exception (rate limits, timeouts, etc).
        """
        try:
            response = self._client.models.generate_content(
                model="gemini-2.5-flash-lite",
                contents=prompt,
                config=self._generate_config,
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error ({type(e).__name__}): {e}")
            raise

    def explain(
        self,
        raw_text: str,
        context_type: ContextType,
        tokens: list[Token]
    ) -> dict:
        """
        Generate educational explanation for Japanese text.

        Args:
            raw_text: The extracted Japanese text from OCR
            context_type: The classified context (sign, menu, etc)
            tokens: Pre-analyzed tokens from NLPService

        Returns:
            Parsed dict matching the response schema in SYSTEM_PROMPT.
            Raises ValueError if the response cannot be parsed.
        """
        if not self._initialized:
            raise RuntimeError("AIService not initialized. Call initialize() first.")

        prompt = self._build_user_prompt(raw_text, context_type, tokens)

        logger.info(f"Calling Gemini for text: {raw_text[:50]}...")
        raw_response = self._call_api(prompt)

        try:
            result = json.loads(raw_response)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini response as JSON: {e}")
            logger.error(f"Raw response was: {raw_response}")
            raise ValueError(f"AI returned invalid JSON: {e}")

        return result


# Module-level singleton
ai_service = AIService()