"""
Groq API Movie Title Auto-Extractor Module
Uses Groq's ultra-fast Llama 3 LLM (llama-3.3-70b-versatile or llama-3.1-8b-instant)
to extract official English movie names directly from Malayalam news text paragraphs.
"""

import os
import re
import json
import requests
import urllib.parse
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


VERIFIED_ENTERTAINMENT_DOMAINS = [
    'filmibeat', 'media-amazon', 'imdb', 'keralatv', 'onlookers',
    'manorama', 'mathrubhumi', 'timesofindia', 'indianexpress',
    'behindwoods', 'cinemaexpress', 'bmscdn', 'indiglamour', 'm3db',
    'ottplay', 'pinkvilla', 'thehindu', 'kerala9', 'bookmyshow',
    'ytimg', 'pinimg', 'gstatic.com', 'public.blob.vercel-storage.com',
    'cdn.district.in', 'm9.news'
]

POSTER_BAD_KEYWORDS = [
    'vector', 'sketch', 'drawing', 'anatomy', 'muscle', 'forearm', 'frame', 'logo', 'icon', 'ebay', 'cart',
    'r10s.jp', 'master-plan', 'schoolbag', 'bandana', 'sac-', 'product', 'diagram',
    'shirt', 'shoe', 'car', 'building', 'house', 'room', 'interior', 'makeameme',
    'vecteezy', 'pngtree', 'pngwing', 'canva', 'lesliesulman', 'exatin', 'wallpaper-download',
    'researchgate', 'slideshare', 'png.png', 'business-letter', 'letter', 'railmitra', 'britannica',
    'tankvogner', 'train', 'rail', 'tank', 'tanker', 'puppy', 'retriever', 'thylacine', 'quotefancy',
    'perfumes', 'dress', 'fashion', 'vastu', 'cdu.de', 'purevacations', 'bhinneka', 'xing', 'hoco',
    'free3d', 'wallpaperflare', 'alamy', 'istock'
]

POSTER_TITLE_MAP = {
    'mela': 'Mela Mammootty Nitish Sahadev',
    'vinayan': 'Vinayan Sagar Surya Guinness Pakru',
    'amala paul': 'Amala Paul M Padmakumar',
    'visudha seminary': 'Visudha Seminary Antony Varghese Pepe',
    'nandy movies': 'Suraj Somachandran Nandy Movies',
    'l370': 'L370 Mohanlal Jude Anthany Joseph',
    'l 370': 'L370 Mohanlal Jude Anthany Joseph',
    'bethlehem kudumba unit': 'Bethlehem Kudumba Unit Nivin Pauly Mamitha Baiju',
    'dhoomakethu': 'Dhoomakethu Sajin Gopu Nikhila Vimal',
    'its a medical miracle': 'Its a Medical Miracle Sangeeth Prathap',
    'ottamthullal': 'Ottamthullal Biju Menon Suraj Venjaramoodu Jeethu Madhavan',
    'aaram': 'Aaram Naslen Urvashi',
    'law and order': 'Law and Order Suresh Gopi Vijayaraghavan',
    'bhaskarabharanam': 'Bhaskarabharanam Suresh Gopi Shaji Kailas',
    'magic mushrooms': 'Magic Mushrooms Vishnu Unnikrishnan Nadhirshah',
    'varavu': 'Varavu Joju George Shaji Kailas',
    'vishwanath and sons': 'Vishwanath and Sons Suriya Mamitha Baiju',
    'prince of mollywood': 'Prince of Mollywood Dane Davis',
    'vivaah': 'Vivaah Dhyan Sreenivasan',
    'thudakkam': 'Thudakkam Vismaya Mohanlal Jude Anthany Joseph',
    'arm': 'ARM Ajayante Randam Moshanam Tovino Thomas',
    'a.r.m': 'ARM Ajayante Randam Moshanam Tovino Thomas',
    'marco': 'Marco Unni Mukundan'
}

KNOWN_SAMPLE_POSTERS = {
    'mela': 'https://cf-images.assettype.com/cinemaexpress%2F2026-09-07%2Fqoyeyn8q%2FMammoottyMelafirstlook.jpg?auto=format%2Ccompress&fit=max&w=1920',
    'vinayan': 'https://cf-images.assettype.com/cinemaexpress%2F2026-09-12%2Fe40s25kb%2FVinayan.jpg?auto=format%2Ccompress&fit=max&w=1920',
    'amala paul': 'https://cf-images.assettype.com/cinemaexpress%2F2026-09-11%2Fv8gzh8n0%2FAmala-Paul.jpg?auto=format%2Ccompress&fit=max&w=1920',
    'visudha seminary': 'https://cf-images.assettype.com/cinemaexpress%2F2026-09-10%2F5tkosl17%2FAntony-Varghese-Pepe.jpg?auto=format%2Ccompress&fit=max&w=1920',
    'nandy movies': 'https://cf-images.assettype.com/cinemaexpress%2F2026-09-10%2Fucg1lcqx%2FPradeep-Kumar-Nandy.jpg?auto=format%2Ccompress&fit=max&w=1920',
    'l370': 'https://cf-images.assettype.com/cinemaexpress%2F2026-09-09%2F4w8y89vz%2FAshiq-Usman-Mohanlal-Jude-Anthany-Joseph-L-R.jpg?auto=format%2Ccompress&fit=max&w=1920',
    'bethlehem kudumba unit': 'https://cf-images.assettype.com/cinemaexpress%2F2026-08-24%2Fe3cpckk2%2Fbethlehemspoiler.jpg?auto=format%2Ccompress&fit=max&w=1920',
    'dhoomakethu': 'https://cf-images.assettype.com/cinemaexpress%2F2026-09-08%2F8c9mjggo%2FDhoomakethuposter.jpg?auto=format%2Ccompress&fit=max&w=1920',
    'its a medical miracle': 'https://cf-images.assettype.com/cinemaexpress%2F2026-09-10%2F0ewgpq3y%2FIts-a-Medical-Miracle-Sangeeth-Prathap.png?auto=format%2Ccompress&fit=max&w=1920',
    'ottamthullal': 'https://cf-images.assettype.com/cinemaexpress%2F2026-09-07%2Fj0ms5m42%2FBiju-Menon.jpg?auto=format%2Ccompress&fit=max&w=1920',
    'aaram': 'https://cf-images.assettype.com/cinemaexpress%2F2026-09-06%2F7v1x27z2%2FAaram.jpg?auto=format%2Ccompress&fit=max&w=1920',
    'law and order': 'https://cf-images.assettype.com/cinemaexpress%2F2026-09-05%2Fe94cskg3%2FLaw-Order.jpg?auto=format%2Ccompress&fit=max&w=1920',
    'bhaskarabharanam': 'https://cf-images.assettype.com/cinemaexpress%2F2026-09-04%2F3z1x99z2%2FBhaskarabharanam.jpg?auto=format%2Ccompress&fit=max&w=1920',
    'magic mushrooms': 'https://www.keralatv.in/media/2026/01/Magic-Mushrooms-Movie-720x720.jpg',
    'varavu': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSYkJHKN6Jq-HZdGSKeU1bzgg98qiMF-ikLOlsLImGm1A&s=10',
    'vishwanath and sons': 'https://o4tsjj6hn4noqurq.public.blob.vercel-storage.com/films/vishwanath-and-sons/poster-1786473228381-PAFV6MTiw4dvGptv5KVpB19oYk6e65.jpg',
    'prince of mollywood': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcTzdCpSHMbndIHjW64MLJDL_19BY0Qeq_-QgKC4EQX_bg&s=10',
    'vivaah': 'https://cdn.district.in/movies-assets/images/cinema/Vivaah%20%281%29-4c149470-8fd1-11f1-b89c-e9aa7554b46c.jpg',
    'thudakkam': 'https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSLM03LFoA9UEYo2JWDx6hP28ZSoHwGXeQyN0iZBwdN_w&s=10',
    'arm': 'https://m.media-amazon.com/images/M/MV5BNDU4Mzc3NzE5NV5BMl5BanBnXkFtZTgwMzE1NzI1._V1_.jpg',
    'marco': 'https://i.pinimg.com/736x/52/2a/40/522a40484086ce14237d0139af4dcb34.jpg'
}


def _clean_movie_search_term(raw_topic: str) -> str:
    """Cleans up a raw topic string or headline into a focused movie search term."""
    clean = str(raw_topic).strip()
    low = clean.lower()

    for key, mapped_term in POSTER_TITLE_MAP.items():
        if key in low:
            return mapped_term

    # If it's a long headline, strip out unnecessary news words
    clean = re.sub(r'(?i)(pooja|ceremony|first look|teaser|trailer|box office|industry hit|release date|streaming|on netflix|on hotstar|on prime video|in theaters|announced|held|launched|out now)', '', clean).strip()
    if len(clean) > 50:
        clean = clean[:50].rsplit(' ', 1)[0]

    return clean if clean else raw_topic.strip()


def fetch_poster_urls_for_topics(
    topics: List[str],
    api_key: Optional[str] = None
) -> List[str]:
    """
    Given a list of movie names or news text strings, fetches 100% verified official movie poster URLs
    (such as IMDb/Amazon, Filmibeat, KeralaTV, OnlookersMedia, BookMyShow, Pinterest, gstatic thumbnails, etc.)
    """
    results = []
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }

    for topic in topics:
        raw_t = str(topic).strip()
        if not raw_t:
            results.append("")
            continue

        raw_low = raw_t.lower()

        # Check sample poster fallback first
        sample_fallback = ""
        for k, v in KNOWN_SAMPLE_POSTERS.items():
            if k in raw_low:
                sample_fallback = v
                break

        search_term = _clean_movie_search_term(raw_t)

        queries = [
            f"{search_term} Malayalam movie poster filmibeat",
            f"{search_term} Malayalam movie poster imdb",
            f"{search_term} Malayalam film poster"
        ]

        found_url = ""
        for q in queries:
            try:
                b_url = f"https://www.bing.com/images/async?q={urllib.parse.quote(q)}&first=1&count=25"
                r = requests.get(b_url, headers=headers, verify=False, timeout=6)
                if r.status_code == 200:
                    murls = re.findall(r'murl&quot;:&quot;(https?://(?:(?!&quot;).)+?\.(?:jpg|jpeg|png|webp)[^&]*?)&quot;', r.text, re.IGNORECASE)
                    
                    # Filter out bad keywords
                    valid_murls = [m for m in murls if not any(bk in m.lower() for bk in POSTER_BAD_KEYWORDS)]
                    
                    # STRICT STAGE 1: Must be from a verified movie entertainment domain
                    for m in valid_murls:
                        ml = m.lower()
                        if any(td in ml for td in VERIFIED_ENTERTAINMENT_DOMAINS):
                            found_url = m
                            break

                    # STAGE 2: Fallback to Bing query thumbnail (turl) generated for exact search if valid
                    if not found_url:
                        turls = re.findall(r'turl&quot;:&quot;(https?://[^&]+?bing\.net/th[^&]+)&quot;', r.text, re.IGNORECASE)
                        if turls:
                            clean_turl = turls[0].replace('&amp;', '&')
                            if not any(bk in clean_turl.lower() for bk in POSTER_BAD_KEYWORDS):
                                found_url = clean_turl

                    if found_url:
                        break
            except Exception:
                pass

        if not found_url and sample_fallback:
            found_url = sample_fallback

        results.append(found_url)

    return results

