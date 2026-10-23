import os
from typing import Optional

from google import genai
from google.genai import types

from app.prompts import SYSTEM_PROMPT
from app.schemas import LLMResult


def extract_with_gemini(chat_text: str, seller_name: Optional[str] = None) -> LLMResult:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    client = genai.Client(api_key=api_key, http_options=types.HttpOptions(timeout=30_000))
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

    response = client.models.generate_content(
        model=model,
        contents=f"Seller: {seller_name or 'You'}\n\nCHAT:\n{chat_text}",
        config=types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=LLMResult,
            temperature=0,
        ),
    )
    return LLMResult.model_validate_json(response.text)