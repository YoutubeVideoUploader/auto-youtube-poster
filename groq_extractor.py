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
            "1. ABSOLUTELY NO MALAYALAM SCRIPT (NO MALAYALAM CHARACTERS). The entire output headline MUST be written 100% using the English alphabet.\n"
            "2. ALWAYS write Malayalam movie titles phonetically using the English alphabet (e.g. write 'Bethlehem Kudumba Unit' instead of 'ബത്‌ലഹേം കുടുംബ യൂണിറ്റ്', write 'Thudakkam' instead of 'തുടക്കം').\n"
            "3. Never translate Malayalam movie names to literal English meanings (e.g. write 'Thudakkam' instead of 'The Beginning').\n"
            "4. Keep headlines concise, exciting, and limited to 1 line per topic.\n"
            "Return ONLY a JSON object containing an 'items' key with an array of objects in exact order. Example: {\"items\": [{\"headline\": \"Girish A.D. Celebrates 300-Crore Success of 'Bethlehem Kudumba Unit'\"}]}.\n"
            "Do not include any markdown formatting, explanation, or text outside the JSON."
        )
    elif m in ["release_updates"]:
        system_prompt = (
            "You are an expert Malayalam movie news editor. For each topic text below, extract:\n"
            "1. 'movie_name': Official movie title phonetically in English alphabet (e.g. 'Bethlehem Kudumba Unit', 'Thudakkam'). ABSOLUTELY NO MALAYALAM SCRIPT OR MALAYALAM CHARACTERS.\n"
            "2. 'release_date': The theatrical release date EXPLICITLY mentioned in the text (e.g., 'October 2', 'September 25'). CRITICAL: If no release date is mentioned in the text, return '' (an empty string). DO NOT guess, invent, or search for dates outside the text.\n"
            "Return ONLY a JSON object containing an 'items' key with an array of objects in exact order. Example: {\"items\": [{\"movie_name\": \"Bethlehem Kudumba Unit\", \"release_date\": \"October 2\"}]}.\n"
            "Do not include any markdown formatting, explanation, or text outside the JSON."
        )
    else: # ott_updates
        system_prompt = (
            "You are an expert Malayalam movie news editor. For each topic text below, extract:\n"
            "1. 'movie_name': Official movie title phonetically in English alphabet (e.g. 'Bethlehem Kudumba Unit', 'Thudakkam'). ABSOLUTELY NO MALAYALAM SCRIPT OR MALAYALAM CHARACTERS.\n"
            "2. 'release_date': The streaming / OTT release date EXPLICITLY mentioned in the text (e.g., 'September 28', 'Available Now'). CRITICAL: If no release date is mentioned in the text, return '' (an empty string). DO NOT guess, invent, or search for dates outside the text.\n"
            "3. 'ott_platform': The streaming platform name (e.g., 'Netflix', 'Disney+ Hotstar', 'Amazon Prime Video', 'SonyLIV', 'Zee5', 'ManoramaMAX', 'Simply South'). If not mentioned, write ''.\n"
            "Return ONLY a JSON object containing an 'items' key with an array of objects in exact order. Example: {\"items\": [{\"movie_name\": \"Bethlehem Kudumba Unit\", \"release_date\": \"September 28\", \"ott_platform\": \"Netflix\"}]}.\n"
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
                m_text = news_texts[i] if i < len(news_texts) else ""
                if i < len(items) and isinstance(items[i], dict):
                    item = items[i]
                    m_name = str(item.get("movie_name", "")).strip()
                    r_date = str(item.get("release_date", "")).strip()
                    o_plat = str(item.get("ott_platform", "")).strip()

                    if not r_date:
                        r_date = parse_malayalam_date_from_text(m_text)

                    if not o_plat:
                        o_plat = parse_malayalam_platform_from_text(m_text)

                    result.append({
                        "movie_name": m_name,
                        "headline": str(item.get("headline", "")).strip(),
                        "release_date": r_date,
                        "ott_platform": o_plat
                    })
                else:
                    result.append({"movie_name": "", "headline": "", "release_date": "", "ott_platform": ""})
            return result
    except Exception as e:
        print(f"[!] Warning parsing Groq response JSON: {e}")

    return [{"movie_name": "", "headline": "", "release_date": "", "ott_platform": ""}] * len(news_texts)


def parse_malayalam_date_from_text(text: str) -> str:
    """Parses Malayalam date strings like 'സെപ്റ്റംബർ 25ന്' or '25-ന്' into 'September 25'."""
    import re
    if not text:
        return ""

    month_map = {
        'സെപ്റ്റംബർ': 'September', 'സെപ്തംബർ': 'September',
        'ഓഗസ്റ്റ്': 'August', 'ആഗസ്റ്റ്': 'August',
        'ഒക്ടോബർ': 'October', 'നവംബർ': 'November', 'ഡിസംബർ': 'December',
        'ജനുവരി': 'January', 'ഫെബ്രുവരി': 'February', 'മാർച്ച്': 'March',
        'ഏപ്രിൽ': 'April', 'മേയ്': 'May', 'മെയ്': 'May',
        'ജൂൺ': 'June', 'ജൂലൈ': 'July'
    }

    for ml_m, en_m in month_map.items():
        if ml_m in text:
            m_after = re.search(rf'{ml_m}\s*(\d{{1,2}})(?:[\u0D00-\u0D7F\-]*)', text)
            if m_after:
                return f"{en_m} {m_after.group(1)}"

            m_before = re.search(rf'(\d{{1,2}})\s*(?:[\u0D00-\u0D7F\-]*)\s*{ml_m}', text)
            if m_before:
                return f"{en_m} {m_before.group(1)}"

    return ""

def parse_malayalam_platform_from_text(text: str) -> str:
    """Parses Malayalam OTT platform names like 'സീ5ൽ' or 'ഹോട്ട്സ്റ്റാർ'."""
    if not text:
        return ""
    platform_map = [
        (['ഹോട്ട്സ്റ്റാർ', 'hotstar'], 'Jio Hotstar'),
        (['നെറ്റ്ഫ്ലിക്', 'netflix'], 'Netflix'),
        (['സീ5', 'സീ 5', 'zee5', 'zee 5', 'സീ'], 'ZEE5'),
        (['പ്രൈം', 'prime'], 'Prime Video'),
        (['സൺ', 'sunnxt', 'sun nxt'], 'Sun NXT'),
        (['മനോരമ', 'manoramamax'], 'ManoramaMAX'),
        (['സോണി', 'sonyliv'], 'SonyLIV'),
        (['സൈന', 'sainaplay'], 'Saina Play'),
        (['സിംപ്ലി', 'simply south'], 'Simply South')
    ]
    t_low = text.lower()
    for keys, p_name in platform_map:
        for k in keys:
            if k in t_low:
                return p_name
    return ""


def search_release_date_online(movie_name: str, is_ott: bool = False) -> str:
    """Searches online (DuckDuckGo / Wikipedia) for movie release date if missing from news text."""
    import re
    if not movie_name or len(movie_name) < 2:
        return ""

    query = f"{movie_name} Malayalam movie {'OTT' if is_ott else 'theatrical'} release date"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}

    try:
        url = f"https://html.duckduckgo.com/html/?q={requests.utils.quote(query)}"
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code == 200:
            text = resp.text
            months = "January|February|March|April|May|June|July|August|September|October|November|December"
            m = re.search(rf'({months})\s+(\d{{1,2}})(?:,\s*(\d{{4}}))?', text, re.IGNORECASE)
            if m:
                month, day, year = m.group(1), m.group(2), m.group(3)
                return f"{month.capitalize()} {day}" + (f", {year}" if year else "")

            m2 = re.search(rf'(\d{{1,2}})\s+({months})(?:\s+(\d{{4}}))?', text, re.IGNORECASE)
            if m2:
                day, month, year = m2.group(1), m2.group(2), m2.group(3)
                return f"{month.capitalize()} {day}" + (f", {year}" if year else "")
    except Exception:
        pass

    try:
        wiki_url = f"https://en.wikipedia.org/w/api.php?action=query&list=search&srsearch={requests.utils.quote(query)}&utf8=&format=json"
        r = requests.get(wiki_url, headers=headers, timeout=10)
        if r.status_code == 200:
            data = r.json()
            snippets = " ".join([s.get("snippet", "") for s in data.get("query", {}).get("search", [])])
            months = "January|February|March|April|May|June|July|August|September|October|November|December"
            m = re.search(rf'({months})\s+(\d{{1,2}})(?:,\s*(\d{{4}}))?', snippets, re.IGNORECASE)
            if m:
                month, day, year = m.group(1), m.group(2), m.group(3)
                return f"{month.capitalize()} {day}" + (f", {year}" if year else "")
    except Exception:
        pass

    return ""


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
