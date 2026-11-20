import json
import logging
from typing import List, Dict, Any, Optional, Tuple

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# Single isolated function to call LLM (Groq, Gemini, or Mock)
def call_llm(prompt: str, json_mode: bool = False) -> str:
    """
    Isolate the LLM in one module (llm.py) with a single function so it can be swapped.
    Prioritizes GROQ API when GROQ_API_KEY is configured.
    Falls back to Gemini if configured, or returns empty string to use template builder.
    """
    # 1. Groq API
    if settings.is_groq_live:
        try:
            url = "https://api.groq.com/openai/v1/chat/completions"
            headers = {
                "Authorization": f"Bearer {settings.GROQ_API_KEY.strip()}",
                "Content-Type": "application/json"
            }
            models_to_try = [
                settings.GROQ_MODEL or "openai/gpt-oss-120b",
                "qwen/qwen3.8-27b",
                "openai/gpt-oss-20b"
            ]

            system_msg = (
                "You are the Game Master for NPC, an adventure app. "
                "Keep tone playful, concise, and game-like. "
                "When asked for JSON, output valid JSON matching the requested fields exactly."
            )

            for m in models_to_try:
                payload = {
                    "model": m,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.7
                }
                if json_mode:
                    payload["response_format"] = {"type": "json_object"}

                try:
                    resp = httpx.post(url, headers=headers, json=payload, timeout=20.0)
                    if resp.status_code == 200:
                        data = resp.json()
                        choices = data.get("choices", [])
                        if choices:
                            content = choices[0].get("message", {}).get("content", "")
                            if content:
                                return content
                    else:
                        logger.warning(f"Groq model {m} returned {resp.status_code}: {resp.text[:100]}")
                except Exception as ex:
                    logger.warning(f"Error calling Groq with model {m}: {ex}")

        except Exception as e:
            logger.warning(f"Groq API call failed: {e}")

    # 2. Gemini API
    if settings.is_gemini_live:
        try:
            from google import genai
            from google.genai import types

            client = genai.Client(api_key=settings.GEMINI_API_KEY.strip())
            config = types.GenerateContentConfig()
            if json_mode:
                config.response_mime_type = "application/json"

            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=config
            )
            return response.text or ""
        except Exception as e:
            logger.warning(f"Live Gemini LLM call failed: {e}")

    # 3. Fall back to mock
    return ""

def mock_quest_builder(
    category: str,
    experience: Dict[str, Any],
    player_summary: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Template-based quest builder for mock mode or LLM fallback.
    Creates a playful, game-like side quest around the given experience.
    """
    exp_title = experience.get("title", "A mysterious spot")
    exp_id = experience.get("id", "")
    exp_kind = experience.get("kind", "place")
    exp_tag = experience.get("tag", "discovery")
    exp_price = experience.get("price_label")

    free_time = player_summary.get("free_time_minutes", 60)
    duration = min(free_time, 45 if exp_kind == "place" else (90 if exp_kind == "event" else 30))

    difficulty = "easy"
    cost_inr = None
    cost_label = "Cost unknown"

    if exp_price:
        if "free" in exp_price.lower():
            cost_inr = 0
            cost_label = "Free"
        elif "₹" in exp_price or "$" in exp_price:
            cost_inr = 50
            cost_label = "Under ₹100"
    else:
        cost_inr = 0 if category in ["awareness", "explore"] else None
        cost_label = "Free" if cost_inr == 0 else "Cost unknown"

    if category == "explore":
        title = f"Uncover the secrets of {exp_title}"
        description = f"Head to {exp_title}. Walk in, spend at least 20 minutes exploring without checking your phone, and find one detail that isn't mentioned anywhere online."
        why_selected = f"You enjoy exploring new corners of the city and have {free_time} minutes free."
        difficulty = "easy"
        reflection_prompt = "What was the most surprising detail or object you spotted?"
    elif category == "creativity":
        title = f"Capture the vibe at {exp_title}"
        description = f"Visit {exp_title}. Spend 25 minutes observing textures and colors, or try your hand at a quick sketch or craft while you're there."
        why_selected = f"A creative spark at a local {exp_tag} hub tailored to your interests."
        difficulty = "medium"
        duration = min(free_time, 60)
        reflection_prompt = "What artistic detail or idea stood out to you the most?"
    elif category == "social":
        title = f"Exchange greetings at {exp_title}"
        description = f"Drop into {exp_title}. Ask someone there (a host, barista, or fellow visitor) one genuine question about what they recommend here."
        why_selected = "A low-stakes social stretch to connect with someone outside your daily loop."
        difficulty = "medium"
        duration = min(free_time, 30)
        reflection_prompt = "What was their answer, and how did the interaction feel?"
    elif category == "courage":
        title = f"Step outside your comfort zone at {exp_title}"
        description = f"Go to {exp_title}. Order or participate in something you've never tried before. No hesitation, just pure curiosity."
        why_selected = "Courage grows with tiny real-world experiments."
        difficulty = "hard"
        duration = min(free_time, 45)
        reflection_prompt = "What hesitated inside you before you did it, and how do you feel now?"
    else: # awareness
        title = f"Mindful observation at {exp_title}"
        description = f"Sit or stroll around {exp_title} for 15 minutes. Note 5 distinct sounds, 4 physical textures, and 3 subtle movements."
        why_selected = "A grounding awareness pause to reset your sensory baseline."
        difficulty = "easy"
        duration = min(free_time, 20)
        reflection_prompt = "Which sensory detail did you only notice once you stopped to pay attention?"

    return {
        "title": title,
        "description": description,
        "why_selected": why_selected,
        "difficulty": difficulty,
        "duration_minutes": duration,
        "estimated_cost_inr": cost_inr,
        "cost_label": cost_label,
        "reflection_prompt": reflection_prompt,
        "chosen_experience_id": exp_id
    }

def generate_weekly_recap_text(
    stats: Dict[str, Any],
    recent_quests: List[Dict[str, Any]]
) -> Tuple[str, str]:
    """
    Returns (summary_text, generated_by: "llm"|"template")
    """
    quests_completed = stats.get("quests_completed", 0)
    xp_earned = stats.get("xp_earned", 0)
    cats = stats.get("categories_tried", [])

    if settings.is_llm_live:
        prompt = (
            f"Write a 2-sentence encouraging weekly recap for an adventure app user. "
            f"Stats: completed {quests_completed} quests, earned {xp_earned} XP across categories: {', '.join(cats)}. "
            f"Tone: playful, motivating, never guilt-inducing. Exactly 2 sentences."
        )
        llm_resp = call_llm(prompt, json_mode=False)
        if llm_resp and len(llm_resp.strip()) > 10:
            return llm_resp.strip(), "llm"

    # Template fallback
    if quests_completed == 0:
        summary = "A quiet week so far. Quiet weeks count too; one tiny quest whenever you feel ready."
    elif quests_completed == 1:
        summary = f"You broke out of autopilot once this week, earning {xp_earned} XP. One small spark is all it takes to keep momentum alive."
    else:
        summary = f"This week you stepped off the usual path {quests_completed} times and banked {xp_earned} XP across {len(cats)} categories. Your city is officially your playground."

    return summary, "template"
