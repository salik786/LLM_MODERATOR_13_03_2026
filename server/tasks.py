# ============================================================
# tasks.py - Standardized Tasks for Research Study
# ============================================================

DESERT_SURVIVAL_ITEMS = [
    "A flashlight (4 battery size)",
    "A map of the region",
    "A compass",
    "A large plastic sheet",
    "A box of matches",
    "A winter coat",
    "A bottle of salt tablets (1000 tablets)",
    "A small knife",
    "2 quarts of water per person",
    "A cosmetic mirror",
    "A parachute (red & white)",
    "A book - 'Edible Animals of the Desert'"
]

# Expert ranking for reference (from survival experts)
EXPERT_RANKING = {
    "A cosmetic mirror": 1,  # Most important (signaling)
    "2 quarts of water per person": 2,
    "A flashlight": 3,
    "A parachute": 4,
    "A small knife": 5,
    "A large plastic sheet": 6,
    "A box of matches": 7,
    "A winter coat": 8,
    "A compass": 9,
    "A map of the region": 10,
    "A bottle of salt tablets": 11,
    "A book - 'Edible Animals of the Desert'": 12
}

TASKS = {
    "desert_survival": {
        "name": "Desert Survival Scenario",
        "description": """
You and your two teammates are survivors of a small plane crash in a remote desert area.
The pilot and co-pilot did not survive. The plane burned after impact.

It is midday in summer. The temperature is extremely high. You estimate the nearest 
known settlement is approximately 100 kilometers away.

Before the crash, the plane was carrying several items. After the crash, you were able 
to recover the following 12 items.

Your task as a group is to:
1. Rank the items from 1 (most important for survival) to 12 (least important).
2. Agree on one final group ranking.
3. Be prepared to briefly explain your reasoning.

You must reach a group consensus within 15-20 minutes.
""",
        "items": DESERT_SURVIVAL_ITEMS,
        "expert_ranking": EXPERT_RANKING,
        "duration_minutes": 15
    }
}

def get_task(task_id="desert_survival"):
    """Get the standardized research task"""
    return TASKS.get(task_id, TASKS["desert_survival"])