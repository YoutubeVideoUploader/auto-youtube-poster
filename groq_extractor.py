"""
Groq API Movie Title Auto-Extractor Module
Uses Groq's ultra-fast Llama 3 LLM (llama-3.3-70b-versatile or llama-3.1-8b-instant)
to extract official English movie names directly from Malayalam news text paragraphs.
"""

import os
import json
import requests
from typing import List, Dict, Any, Optional

DEFAULT_GROQ_MODEL = "openai/gpt-oss-20b"
CANDIDATE_GROQ_MODELS = [
    "openai/gpt-oss-20b",
    "openai/gpt-oss-120b",
    "qwen/qwen3.8-27b",
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant"
]


def extract_movie_titles_with_groq(
    news_texts: List[str],
    api_key: Optional[str] = None,
    model: str = DEFAULT_GROQ_MODEL,
    mode: str = "movie_name"
) -> List[str]:
    """
    Given a list of Malayalam news text strings, uses Groq API to extract:
    - If mode == "headline" or "movie_updates": A 1-line English topic headline/heading.
    - Else ("movie_name" / "release_updates" / "ott_updates"): The exact phonetic English movie name.
    Returns a list of extracted strings matching the input list order.
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

    is_headline_mode = mode in ["headline", "movie_updates", "Movie Updates"]

    if is_headline_mode:
        system_prompt = (
            "You are an expert Malayalam movie news editor. For each topic text below, generate a short, catchy 1-line English Headline / Topic Heading summarizing the news.\n"
            "CRITICAL RULES:\n"
            "1. Never translate Malayalam movie names to English meanings (e.g. write 'Thudakkam' instead of 'The Beginning').\n"
            "2. Keep headlines concise, exciting, and limited to 1 line per topic (e.g., 'Thudakkam Movie Pooja Ceremony Held in Kochi').\n"
            "3. Return ONLY a JSON object containing a 'titles' key with an array of string headlines in exact order. Example: {\"titles\": [\"Thudakkam Movie Pooja Held\", \"Avarachan & Sons Release Date Announced\"]}.\n"
            "Do not include any markdown formatting, explanation, or text outside the JSON."
        )
    else:
        system_prompt = (
            "You are an expert Malayalam movie news editor. Extract the official movie title for each topic text below.\n"
            "CRITICAL RULE: Never translate Malayalam words to English meanings (for example, NEVER write 'The Beginning' for 'തുടക്കം'). "
            "Always phonetically transliterate the Malayalam movie title using English alphabet (e.g., write 'Thudakkam'). "
            "If the title is an established English title, keep it as is.\n"
            "Return ONLY a JSON object containing a 'titles' key with an array of string titles corresponding to each topic in exact order. "
            "Example response format: {\"titles\": [\"Thudakkam\", \"Avarachan and Sons\"]}. "
            "Do not include any markdown formatting, explanation, or text outside the JSON."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    url = "https://api.groq.com/openai/v1/chat/completions"
    
    models_to_try = [model] + [m for m in CANDIDATE_GROQ_MODELS if m != model]
    last_error = ""
    response = None

    for candidate in models_to_try:
        payload = {
            "model": candidate,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.1,
            "response_format": {"type": "json_object"}
        }

        try:
            res = requests.post(url, headers=headers, json=payload, timeout=25, verify=False)
            if res.status_code == 200:
                response = res
                break
            else:
                last_error = f"Model '{candidate}' failed (HTTP {res.status_code}): {res.text}"
        except Exception as e:
            last_error = f"Model '{candidate}' exception: {e}"

    if not response or response.status_code != 200:
        raise RuntimeError(f"Groq API call failed across all candidate models. Last error: {last_error}")

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
