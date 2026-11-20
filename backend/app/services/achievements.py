from typing import List, Dict, Optional, Tuple
from app.schemas import Achievement, Category

ALL_ACHIEVEMENTS: List[Dict[str, str]] = [
    {
        "id": "first_step",
        "name": "First Step",
        "description": "Complete your first side quest.",
        "icon_key": "footprint"
    },
    {
        "id": "explorer",
        "name": "Explorer",
        "description": "Complete 3 explore quests.",
        "icon_key": "compass"
    },
    {
        "id": "social_spark",
        "name": "Social Spark",
        "description": "Complete 2 social quests.",
        "icon_key": "spark"
    },
    {
        "id": "maker",
        "name": "Maker",
        "description": "Complete 2 creativity quests.",
        "icon_key": "brush"
    },
    {
        "id": "brave_heart",
        "name": "Brave Heart",
        "description": "Complete 1 courage quest.",
        "icon_key": "heart"
    },
    {
        "id": "present",
        "name": "Present",
        "description": "Complete 2 awareness quests.",
        "icon_key": "eye"
    },
    {
        "id": "variety_pack",
        "name": "Variety Pack",
        "description": "Complete a quest in every category.",
        "icon_key": "dice"
    },
    {
        "id": "local_legend",
        "name": "Local Legend",
        "description": "Complete 10 quests.",
        "icon_key": "crown"
    }
]

def evaluate_achievements(
    quests_completed: int,
    category_counts: Dict[str, int],
    currently_unlocked_ids: set,
    now_iso: str
) -> Tuple[List[Achievement], List[Achievement]]:
    """
    Returns (all_achievements, newly_unlocked_achievements)
    """
    all_res: List[Achievement] = []
    newly_unlocked: List[Achievement] = []

    all_categories = {"explore", "social", "creativity", "courage", "awareness"}

    for a in ALL_ACHIEVEMENTS:
        aid = a["id"]
        is_already_unlocked = aid in currently_unlocked_ids

        qualifies = False
        if aid == "first_step":
            qualifies = quests_completed >= 1
        elif aid == "explorer":
            qualifies = category_counts.get("explore", 0) >= 3
        elif aid == "social_spark":
            qualifies = category_counts.get("social", 0) >= 2
        elif aid == "maker":
            qualifies = category_counts.get("creativity", 0) >= 2
        elif aid == "brave_heart":
            qualifies = category_counts.get("courage", 0) >= 1
        elif aid == "present":
            qualifies = category_counts.get("awareness", 0) >= 2
        elif aid == "variety_pack":
            qualifies = all(category_counts.get(c, 0) >= 1 for c in all_categories)
        elif aid == "local_legend":
            qualifies = quests_completed >= 10

        if not is_already_unlocked and qualifies:
            ach = Achievement(
                id=aid,
                name=a["name"],
                description=a["description"],
                icon_key=a["icon_key"],
                unlocked=True,
                unlocked_at=now_iso
            )
            newly_unlocked.append(ach)
            all_res.append(ach)
        else:
            all_res.append(
                Achievement(
                    id=aid,
                    name=a["name"],
                    description=a["description"],
                    icon_key=a["icon_key"],
                    unlocked=is_already_unlocked,
                    unlocked_at=now_iso if is_already_unlocked else None
                )
            )

    return all_res, newly_unlocked

