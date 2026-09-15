"""
Groq API Movie Title Auto-Extractor Module
Uses Groq's ultra-fast Llama 3 LLM (llama-3.3-70b-versatile or llama-3.1-8b-instant)
to extract official English movie names directly from Malayalam news text paragraphs.
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional

DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
FAST_GROQ_MODEL = "llama-3.1-8b-instant"


def extract_movie_titles_with_groq(
    news_texts: List[str],
    api_key: Optional[str] = None,
    model: str = DEFAULT_GROQ_MODEL
) -> List[str]:
    """
    Given a list of Malayalam news text strings, uses Groq API to extract the official English movie title for each topic.
    Returns a list of extracted English movie title strings matching the input list order.
    """
    api_key = api_key or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("Groq API Key is missing. Please enter your Groq API Key.")

    if not news_texts:
        return []

    # Build prompt items
    formatted_topics = []
    for idx, text in enumerate(news_texts, start=1):
        clean_t = str(text).strip()
        formatted_topics.append(f"Topic #{idx}: {clean_t if clean_t else 'No text'}")

    user_prompt = "\n".join(formatted_topics)

    system_prompt = (
        "You are an expert Malayalam movie news editor. Extract the official English movie name/title for each topic text below. "
        "Return ONLY a JSON object containing a 'titles' key with an array of string titles corresponding to each topic in exact order. "
        "Example response format: {\"titles\": [\"Dhoomakethu\", \"Loki\", \"Mela\"]}. "
        "Do not include any markdown formatting, explanation, or text outside the JSON."
    )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1,
        "response_format": {"type": "json_object"}
    }

    url = "https://api.groq.com/openai/v1/chat/completions"
    
    try:
        response = requests.post(url, headers=headers, json=payload, timeout=25)
    except Exception as e:
        raise RuntimeError(f"Network error calling Groq API: {e}")

    if response.status_code != 200:
        # Fallback to fast model if model failed
        if model != FAST_GROQ_MODEL:
            payload["model"] = FAST_GROQ_MODEL
            try:
                response = requests.post(url, headers=headers, json=payload, timeout=25)
            except Exception:
                pass

    if response.status_code != 200:
        raise RuntimeError(f"Groq API call failed (HTTP {response.status_code}): {response.text}")

    data = response.json()
    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")

    try:
        parsed = json.loads(content)
        titles = parsed.get("titles", [])
        if isinstance(titles, list):
            result = []
            for i in range(len(news_texts)):
                if i < len(titles) and isinstance(titles[i], str):
                    result.append(titles[i].strip())
                else:
                    result.append("")
            return result
    except Exception as e:
        print(f"[!] Warning parsing Groq response JSON: {e}")

    return [""] * len(news_texts)
