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


def extract_metadata_with_groq(
    news_texts: List[str],
    api_key: Optional[str] = None,
    model: str = DEFAULT_GROQ_MODEL,
    mode: str = "movie_updates"
) -> List[Dict[str, str]]:
    """
    Given a list of Malayalam news text strings, uses Groq API to extract metadata:
    - Movie Updates: headline
    - Release Updates: movie_name, release_date
    - OTT Updates: movie_name, release_date, ott_platform
    Returns a list of dict objects matching the input list order.
    """
    api_key = api_key or os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise ValueError("Groq API Key is missing. Please enter your Groq API Key.")

    if not news_texts:
        return []

    formatted_topics = []
    for idx, text in enumerate(news_texts, start=1):
        clean_t = str(text).strip()
        formatted_topics.append(f"Topic #{idx}: {clean_t if clean_t else 'No text'}")

    user_prompt = "\n".join(formatted_topics)

    m = mode.lower().replace(" ", "_")

    if m in ["movie_updates", "headline"]:
        system_prompt = (
            "You are an expert Malayalam movie news editor. For each topic text below, generate a short, catchy 1-line English Headline / Topic Heading summarizing the news.\n"
            "CRITICAL RULES:\n"
            "1. Never translate Malayalam movie names to English meanings (e.g. write 'Thudakkam' instead of 'The Beginning').\n"
            "2. Keep headlines concise, exciting, and limited to 1 line per topic.\n"
            "3. Return ONLY a JSON object containing an 'items' key with an array of objects in exact order. Example: {\"items\": [{\"headline\": \"Thudakkam Movie Pooja Held\"}]}.\n"
            "Do not include any markdown formatting, explanation, or text outside the JSON."
        )
    elif m in ["release_updates"]:
        system_prompt = (
            "You are an expert Malayalam movie news editor. For each topic text below, extract:\n"
            "1. 'movie_name': Official movie title phonetically in English alphabet (never translate Malayalam names to English meanings, e.g. write 'Thudakkam' instead of 'The Beginning').\n"
            "2. 'release_date': The theatrical release date mentioned (e.g., 'October 2', 'This Friday', 'Deepavali 2026'). If not mentioned, write ''.\n"
            "Return ONLY a JSON object containing an 'items' key with an array of objects in exact order. Example: {\"items\": [{\"movie_name\": \"Thudakkam\", \"release_date\": \"October 2\"}]}.\n"
            "Do not include any markdown formatting, explanation, or text outside the JSON."
        )
    else: # ott_updates
        system_prompt = (
            "You are an expert Malayalam movie news editor. For each topic text below, extract:\n"
            "1. 'movie_name': Official movie title phonetically in English alphabet (never translate Malayalam names to English meanings, e.g. write 'Thudakkam' instead of 'The Beginning').\n"
            "2. 'release_date': The streaming / OTT release date mentioned (e.g., 'September 28', 'Available Now'). If not mentioned, write ''.\n"
            "3. 'ott_platform': The streaming platform name (e.g., 'Netflix', 'Disney+ Hotstar', 'Amazon Prime Video', 'SonyLIV', 'Zee5', 'ManoramaMAX', 'Simply South'). If not mentioned, write ''.\n"
            "Return ONLY a JSON object containing an 'items' key with an array of objects in exact order. Example: {\"items\": [{\"movie_name\": \"Thudakkam\", \"release_date\": \"September 28\", \"ott_platform\": \"Netflix\"}]}.\n"
            "Do not include any markdown formatting, explanation, or text outside the JSON."
        )

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    url = "https://api.groq.com/openai/v1/chat/completions"
    
    models_to_try = [model] + [cand for cand in CANDIDATE_GROQ_MODELS if cand != model]
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
        items = parsed.get("items", [])
        if isinstance(items, list):
            result = []
            for i in range(len(news_texts)):
                if i < len(items) and isinstance(items[i], dict):
                    item = items[i]
                    result.append({
                        "movie_name": str(item.get("movie_name", "")).strip(),
                        "headline": str(item.get("headline", "")).strip(),
                        "release_date": str(item.get("release_date", "")).strip(),
                        "ott_platform": str(item.get("ott_platform", "")).strip()
                    })
                else:
                    result.append({"movie_name": "", "headline": "", "release_date": "", "ott_platform": ""})
            return result
    except Exception as e:
        print(f"[!] Warning parsing Groq response JSON: {e}")

    return [{"movie_name": "", "headline": "", "release_date": "", "ott_platform": ""}] * len(news_texts)


def extract_movie_titles_with_groq(
    news_texts: List[str],
    api_key: Optional[str] = None,
    model: str = DEFAULT_GROQ_MODEL,
    mode: str = "movie_name"
) -> List[str]:
    """
    Backwards-compatible wrapper returning string list.
    """
    metadata_list = extract_metadata_with_groq(news_texts, api_key=api_key, model=model, mode=mode)
    res = []
    m = mode.lower().replace(" ", "_")
    for item in metadata_list:
        if m in ["movie_updates", "headline"]:
            res.append(item.get("headline") or item.get("movie_name") or "")
        else:
            res.append(item.get("movie_name") or "")
    return res
