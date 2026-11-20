from datetime import datetime, timezone, timedelta
from typing import List, Tuple
from app.schemas import Autopilot, Preferences, AutopilotLabel

DISCLAIMER = "A playful reflection of your reported habits. Not a psychological score."

def calculate_autopilot(prefs: Preferences, recent_completions: List[Tuple[str, str]]) -> Autopilot:
    """
    recent_completions: list of (completed_at_iso, category)
    """
    score = 50

    # novelty_frequency
    nf_adj = {
        "rarely": 25,
        "monthly": 10,
        "weekly": -10,
        "daily": -25
    }
    score += nf_adj.get(prefs.novelty_frequency, 0)

    # last_first_time
    lft_adj = {
        "this_week": -15,
        "this_month": -5,
        "this_year": 10,
        "cant_remember": 20
    }
    score += lft_adj.get(prefs.last_first_time, 0)

    # comfort_level (5 = comfortable with new things)
    # -4 per point above 3 and +4 per point below 3
    # i.e. (3 - comfort_level) * 4
    score += (3 - prefs.comfort_level) * 4

    # Completed quests in last 14 days
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=14)

    valid_recent = []
    for c_at, cat in recent_completions:
        try:
            # Handle ISO timestamp parse
            dt = datetime.fromisoformat(c_at.replace("Z", "+00:00"))
            if dt >= cutoff:
                valid_recent.append((dt, cat))
        except Exception:
            pass

    quest_deduction = min(30, len(valid_recent) * 4)
    distinct_categories = len(set(cat for _, cat in valid_recent))
    cat_deduction = min(15, distinct_categories * 3)

    score -= quest_deduction
    score -= cat_deduction

    # Clamp 0..100
    score = max(0, min(100, int(round(score))))

    if score < 25:
        label: AutopilotLabel = "Wide awake"
        explanation = "You've been trying lots of new things lately. Keep the curiosity rolling."
    elif score < 50:
        label = "Mostly exploring"
        explanation = "Plenty of fresh moments in your week, with a comfy routine underneath."
    elif score < 75:
        label = "Needs a little adventure"
        explanation = "Higher means more repetition. A small first-time could tip the scale."
    else:
        label = "Deep autopilot"
        explanation = "Higher means more repetition. Your days look familiar right now, and that's okay. One tiny quest is enough."

    return Autopilot(
        score=score,
        label=label,
        explanation=explanation,
        disclaimer=DISCLAIMER
    )

