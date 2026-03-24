"""
NutriVeda Diet Plan Generator
Generates a personalized weekly diet & fitness plan (Mon–Sun).
Calorie-focused, globally aware, simple and professional.
"""

import os
import re
import asyncio
import logging
from typing import Tuple, List, Callable, Awaitable, Optional
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

from rag.retrieval import retrieve_relevant_context, build_client_query
from diet.calculator import CalorieTargets

log = logging.getLogger(__name__)

_openai_client = None

def get_client():
    global _openai_client
    if _openai_client is None:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY not set in .env file")
        _openai_client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://openrouter.ai/api/v1",
            default_headers={
                "HTTP-Referer": "https://nutriveda.vercel.app",
                "X-Title": "NutriVeda",
            },
        )
    return _openai_client


DIET_TYPE_NOTES = {
    "vegetarian": "No meat, no fish, no eggs. Dairy (milk, paneer, curd, ghee) is allowed.",
    "non_vegetarian": "All foods allowed — chicken, fish, eggs, meat, dairy.",
    "eggetarian": "Vegetarian + eggs allowed. No meat or fish.",
    "vegan": "No animal products at all — no dairy, no eggs, no meat, no honey.",
    "jain": "No root vegetables (onion, garlic, potato, carrot, beet). Strictly vegetarian.",
}

PROTEIN_INTAKE_NOTES = {
    "none_low": (
        "Client is currently on a low-protein diet with no supplements. "
        "START GENTLY — introduce protein gradually via familiar foods (dal, eggs, paneer, chicken, curd). "
        "Do NOT overwhelm with high protein from day one. Build up slowly over the week. "
        "Educate on simple protein sources in meals."
    ),
    "none_moderate": (
        "Client already eats moderate protein through food (eggs, chicken, dal, paneer). "
        "No supplements currently. Optimize protein distribution — spread evenly across all 4–5 meals. "
        "Focus on quality sources and timing. Supplements optional but not required at this stage."
    ),
    "supplements": (
        "Client is actively taking protein supplements (whey or plant protein). "
        "Include one protein shake in the plan (pre or post workout). "
        "Add exact serving size and timing. Combine with whole-food protein sources for best results. "
        "Make sure total protein from food + shake meets the {protein}g daily target."
    ),
    "high_food": (
        "Client already follows a high-protein diet through whole foods only — no supplements. "
        "Maintain their protein habits. Focus on optimizing protein quality (complete vs incomplete), "
        "meal distribution, and variety across the week. No need to introduce supplements."
    ),
    "not_sure": (
        "Client is unsure about their protein intake. "
        "Include simple, approachable protein sources (eggs, dal, chicken, paneer, curd, legumes). "
        "Add a brief educational note on protein in the plan — keep it simple and non-technical. "
        "Start with moderate protein targets and do not overwhelm."
    ),
}

GOAL_LABELS = {
    "lose_weight": "Lose Weight",
    "gain_muscle": "Build Muscle",
    "gain_muscle_lose_fat": "Build Muscle & Lose Fat",
    "maintain": "Maintain Weight",
    "medical_management": "Medical Nutrition",
    "improve_health": "Improve Health",
    "sports_nutrition": "Sports Performance",
}

# ── Verified Nutrition Reference Table ──────────────────────────────────────
# Values per 100g (or per unit where noted). Source: USDA FoodData Central + Indian IFCT.
# Format: (kcal, protein_g, carbs_g, fat_g)
NUTRITION_DB: dict[str, tuple] = {
    # GRAINS & CEREALS
    "White rice (cooked)":          (130, 2.7, 28.0,  0.3),
    "Brown rice (cooked)":          (123, 2.6, 26.0,  0.9),
    "Roti / chapati":               (260, 7.5, 45.0,  5.0),   # per 100g (1 piece ~40g = 104 kcal)
    "Whole wheat bread":            (242, 10.9, 42.4, 4.2),   # per 100g (1 slice ~33g = 80 kcal)
    "White bread":                  (267, 8.0, 50.0,  3.3),   # per 100g (1 slice ~30g = 80 kcal)
    "Oats (dry, raw)":              (389, 17.0, 66.0,  7.0),
    "Oats (cooked)":                (71,  2.5, 12.0,  1.5),
    "Idli":                         (116, 3.8, 24.0,  0.8),   # per 100g (1 piece ~50g = 58 kcal)
    "Dosa (plain)":                 (150, 3.5, 22.5,  5.0),   # per 100g (1 medium ~80g = 120 kcal)
    "Upma (cooked)":                (120, 3.0, 18.0,  4.0),
    "Poha (cooked)":                (110, 2.0, 22.0,  2.0),
    "Wheat flour / atta (dry)":     (340, 12.0, 72.0, 1.8),
    "Semolina / suji (dry)":        (360, 11.0, 74.0, 1.0),
    "Quinoa (cooked)":              (120, 4.4, 22.0,  1.9),
    "Pasta / noodles (cooked)":     (158, 5.8, 31.0,  0.9),
    # MEAT, FISH & EGGS
    "Chicken breast (cooked)":      (165, 31.0,  0.0,  3.6),
    "Chicken thigh (cooked)":       (209, 26.0,  0.0, 11.0),
    "Whole egg":                    (156, 13.0,  1.2, 11.0),   # per 100g (1 large ~50g = 78 kcal)
    "Egg white":                    (52,  10.9,  0.6,  0.3),   # per 100g (1 large ~33g = 17 kcal)
    "Fish fillet (cooked, generic)":(130, 24.0,  0.0,  3.0),
    "Salmon (cooked)":              (208, 20.0,  0.0, 13.0),
    "Tuna (canned in water)":       (132, 29.0,  0.0,  1.0),
    "Mutton / lamb (cooked)":       (218, 21.0,  0.0, 14.0),
    "Prawn / shrimp (cooked)":      (99,  24.0,  0.9,  0.3),
    # DAIRY
    "Full-fat milk":                (61,  3.2,   4.8,  3.3),
    "Low-fat milk":                 (42,  3.5,   5.0,  1.0),
    "Paneer":                       (296, 18.0,  4.3, 23.0),
    "Curd / yogurt (full-fat)":     (60,  3.5,   4.0,  3.3),
    "Curd / yogurt (low-fat)":      (45,  4.0,   5.0,  0.5),
    "Greek yogurt":                 (59,  10.0,  3.6,  0.4),
    "Whey protein":                 (400, 83.3, 10.0,  5.0),   # per 100g (1 scoop ~30g = 120 kcal)
    "Cheese (cheddar)":             (402, 25.0,  1.3, 33.0),
    "Buttermilk / chaas":           (40,  3.3,   5.0,  1.0),
    # LEGUMES (cooked)
    "Toor dal / arhar dal (cooked)":(116,  7.0, 20.0,  0.4),
    "Moong dal (cooked)":           (105,  7.0, 19.0,  0.4),
    "Masoor dal (cooked)":          (116,  9.0, 20.0,  0.4),
    "Chana dal (cooked)":           (164,  9.0, 27.0,  2.7),
    "Rajma / kidney beans (cooked)":(127,  8.7, 22.0,  0.5),
    "Chickpeas / chana (cooked)":   (164,  8.9, 27.0,  2.6),
    "Black-eyed beans (cooked)":    (136,  9.0, 24.0,  0.6),
    "Tofu":                         (76,   8.0,  2.0,  4.2),
    # VEGETABLES
    "Spinach (cooked)":             (23,   3.0,  3.7,  0.3),
    "Broccoli (cooked)":            (35,   2.4,  7.0,  0.4),
    "Cauliflower (cooked)":         (23,   1.9,  5.0,  0.3),
    "Carrot (raw)":                 (41,   0.9, 10.0,  0.2),
    "Tomato (raw)":                 (18,   0.9,  3.9,  0.2),
    "Onion (raw)":                  (40,   1.1,  9.3,  0.1),
    "Cucumber (raw)":               (16,   0.7,  3.6,  0.1),
    "Bottle gourd / lauki (cooked)":(14,   0.6,  3.5,  0.1),
    "Okra / bhindi (cooked)":       (33,   1.9,  7.5,  0.2),
    "Bell pepper / capsicum":       (31,   1.0,  6.0,  0.3),
    "Green peas (cooked)":          (84,   5.4, 15.0,  0.4),
    "Sweet potato (cooked)":        (90,   2.0, 21.0,  0.1),
    "Potato (boiled)":              (87,   1.9, 20.0,  0.1),
    "Bitter gourd / karela":        (25,   1.0,  5.5,  0.2),
    "Mushrooms (cooked)":           (28,   2.2,  5.3,  0.4),
    # FRUITS
    "Banana":                       (89,   1.1, 23.0,  0.3),
    "Apple":                        (52,   0.3, 14.0,  0.2),
    "Mango":                        (60,   0.8, 15.0,  0.4),
    "Orange":                       (47,   0.9, 12.0,  0.1),
    "Papaya":                       (43,   0.5, 11.0,  0.3),
    "Watermelon":                   (30,   0.6,  8.0,  0.2),
    "Grapes":                       (69,   0.7, 18.0,  0.2),
    "Avocado":                      (160,  2.0,  9.0, 15.0),
    "Date":                         (250,  2.5, 67.5,  0.0),   # per 100g (1 piece ~8g = 20 kcal)
    "Pomegranate":                  (83,   1.7, 19.0,  1.2),
    # FATS & OILS (per 100g — use small amounts, e.g. 5–10g per meal)
    "Ghee":                         (900,  0.0,  0.0,100.0),
    "Coconut oil":                  (862,  0.0,  0.0,100.0),
    "Olive oil":                    (884,  0.0,  0.0,100.0),
    "Butter":                       (717,  0.9,  0.1, 81.0),
    # NUTS & SEEDS
    "Almonds":                      (579, 21.0, 22.0, 50.0),
    "Cashews":                      (553, 18.0, 30.0, 44.0),
    "Walnuts":                      (654, 15.0, 14.0, 65.0),
    "Peanuts":                      (567, 26.0, 16.0, 49.0),
    "Mixed nuts":                   (607, 20.0, 21.0, 54.0),
    "Pumpkin seeds":                (559, 30.0, 11.0, 49.0),
    "Flaxseeds":                    (534, 18.0, 29.0, 42.0),
    "Chia seeds":                   (486, 17.0, 42.0, 31.0),
    # BEVERAGES (per 100 ml)
    "Lassi (sweet)":                (80,   3.0, 10.0,  3.0),
    "Lassi (salted)":               (50,   2.5,  4.0,  2.5),
    "Coconut water":                (19,   0.7,  4.7,  0.2),
    "Green tea":                    (2,    0.0,  0.5,  0.0),
    "Sambar":                       (50,   2.5,  8.0,  1.0),
    "Coconut chutney":              (180,  2.0,  6.0, 17.0),
}


# ── Food category tags ───────────────────────────────────────────────────────
# Used to guide GPT into building balanced meals: grain + protein + veg + fat
FOOD_CATEGORIES: dict[str, str] = {
    "White rice (cooked)": "grain", "Brown rice (cooked)": "grain",
    "Roti / chapati": "grain", "Whole wheat bread": "grain",
    "White bread": "grain", "Oats (dry, raw)": "grain",
    "Oats (cooked)": "grain", "Idli": "grain",
    "Dosa (plain)": "grain", "Upma (cooked)": "grain",
    "Poha (cooked)": "grain", "Wheat flour / atta (dry)": "grain",
    "Semolina / suji (dry)": "grain", "Quinoa (cooked)": "grain",
    "Pasta / noodles (cooked)": "grain",
    "Chicken breast (cooked)": "protein", "Chicken thigh (cooked)": "protein",
    "Whole egg": "protein", "Egg white": "protein",
    "Fish fillet (cooked, generic)": "protein", "Salmon (cooked)": "protein",
    "Tuna (canned in water)": "protein", "Mutton / lamb (cooked)": "protein",
    "Prawn / shrimp (cooked)": "protein",
    "Full-fat milk": "dairy", "Low-fat milk": "dairy", "Paneer": "protein",
    "Curd / yogurt (full-fat)": "dairy", "Curd / yogurt (low-fat)": "dairy",
    "Greek yogurt": "dairy", "Whey protein": "protein",
    "Cheese (cheddar)": "dairy", "Buttermilk / chaas": "dairy",
    "Toor dal / arhar dal (cooked)": "protein", "Moong dal (cooked)": "protein",
    "Masoor dal (cooked)": "protein", "Chana dal (cooked)": "protein",
    "Rajma / kidney beans (cooked)": "protein", "Chickpeas / chana (cooked)": "protein",
    "Black-eyed beans (cooked)": "protein", "Tofu": "protein",
    "Spinach (cooked)": "veg", "Broccoli (cooked)": "veg",
    "Cauliflower (cooked)": "veg", "Carrot (raw)": "veg",
    "Tomato (raw)": "veg", "Onion (raw)": "veg", "Cucumber (raw)": "veg",
    "Bottle gourd / lauki (cooked)": "veg", "Okra / bhindi (cooked)": "veg",
    "Bell pepper / capsicum": "veg", "Green peas (cooked)": "veg",
    "Sweet potato (cooked)": "veg", "Potato (boiled)": "veg",
    "Bitter gourd / karela": "veg", "Mushrooms (cooked)": "veg",
    "Banana": "fruit", "Apple": "fruit", "Mango": "fruit", "Orange": "fruit",
    "Papaya": "fruit", "Watermelon": "fruit", "Grapes": "fruit",
    "Avocado": "fat", "Date": "fruit", "Pomegranate": "fruit",
    "Ghee": "fat", "Coconut oil": "fat", "Olive oil": "fat", "Butter": "fat",
    "Almonds": "fat", "Cashews": "fat", "Walnuts": "fat",
    "Peanuts": "fat", "Mixed nuts": "fat", "Pumpkin seeds": "fat",
    "Flaxseeds": "fat", "Chia seeds": "fat",
    "Lassi (sweet)": "beverage", "Lassi (salted)": "beverage",
    "Coconut water": "beverage", "Green tea": "beverage",
    "Sambar": "veg", "Coconut chutney": "fat",
}


def _build_nutrition_table(subset: dict | None = None) -> str:
    """
    Format NUTRITION_DB (or a subset) as a per-gram table for the prompt.
    Values are per-gram (÷100) so GPT formula is: kcal = qty_g × kcal_per_g (no division needed).
    Includes a Category column so GPT builds balanced grain+protein+veg+fat meals.
    """
    db = subset if subset is not None else NUTRITION_DB
    rows = [
        "| Category | Food | kcal/g | P/g | C/g | F/g |",
        "|----------|------|--------|-----|-----|-----|",
    ]
    for food, (kcal, p, c, f) in db.items():
        cat  = FOOD_CATEGORIES.get(food, "other")
        kpg  = round(kcal / 100, 4)
        ppg  = round(p    / 100, 4)
        cpg  = round(c    / 100, 4)
        fpg  = round(f    / 100, 4)
        rows.append(f"| {cat} | {food} | {kpg} | {ppg} | {cpg} | {fpg} |")
    return "\n".join(rows)


# ── Food keys grouped by category for selection ─────────────────────────────
_GRAINS_INDIAN  = ["White rice (cooked)", "Brown rice (cooked)", "Roti / chapati",
                   "Oats (cooked)", "Idli", "Dosa (plain)",
                   "Upma (cooked)", "Poha (cooked)", "Wheat flour / atta (dry)"]
_GRAINS_WESTERN = ["Oats (cooked)", "Whole wheat bread", "White bread",
                   "Pasta / noodles (cooked)", "Quinoa (cooked)", "Brown rice (cooked)"]
_GRAINS_GLOBAL  = ["White rice (cooked)", "Brown rice (cooked)", "Oats (cooked)",
                   "Whole wheat bread", "Quinoa (cooked)", "Pasta / noodles (cooked)"]

_PROTEINS_VEG   = ["Paneer", "Curd / yogurt (full-fat)", "Curd / yogurt (low-fat)", "Greek yogurt",
                   "Full-fat milk", "Low-fat milk", "Buttermilk / chaas",
                   "Toor dal / arhar dal (cooked)", "Moong dal (cooked)", "Masoor dal (cooked)",
                   "Chana dal (cooked)", "Rajma / kidney beans (cooked)", "Chickpeas / chana (cooked)"]
_PROTEINS_VEGAN = ["Tofu", "Toor dal / arhar dal (cooked)", "Moong dal (cooked)", "Masoor dal (cooked)",
                   "Chana dal (cooked)", "Rajma / kidney beans (cooked)", "Chickpeas / chana (cooked)",
                   "Black-eyed beans (cooked)", "Pumpkin seeds", "Chia seeds"]
_PROTEINS_EGG   = ["Whole egg", "Egg white"]
_PROTEINS_MEAT  = ["Chicken breast (cooked)", "Chicken thigh (cooked)", "Mutton / lamb (cooked)"]
_PROTEINS_FISH  = ["Fish fillet (cooked, generic)", "Salmon (cooked)", "Tuna (canned in water)",
                   "Prawn / shrimp (cooked)"]
_PROTEINS_DAIRY = ["Full-fat milk", "Curd / yogurt (full-fat)", "Greek yogurt", "Whey protein"]

_VEGS_INDIAN    = ["Spinach (cooked)", "Cauliflower (cooked)", "Okra / bhindi (cooked)",
                   "Bottle gourd / lauki (cooked)", "Tomato (raw)", "Onion (raw)",
                   "Bitter gourd / karela", "Green peas (cooked)"]
_VEGS_GLOBAL    = ["Spinach (cooked)", "Broccoli (cooked)", "Carrot (raw)", "Tomato (raw)",
                   "Cucumber (raw)", "Bell pepper / capsicum", "Mushrooms (cooked)",
                   "Sweet potato (cooked)", "Potato (boiled)"]

_FRUITS_TROPICAL = ["Banana", "Mango", "Papaya", "Orange", "Pomegranate", "Watermelon", "Date"]
_FRUITS_GLOBAL   = ["Banana", "Apple", "Orange", "Avocado", "Grapes"]

_NUTS_ALL        = ["Almonds", "Walnuts", "Peanuts", "Cashews", "Flaxseeds", "Chia seeds"]
_OILS_INDIAN     = ["Ghee", "Coconut oil"]
_OILS_GLOBAL     = ["Olive oil", "Coconut oil", "Butter"]
_BEVERAGES_INDIAN = ["Lassi (sweet)", "Lassi (salted)", "Buttermilk / chaas", "Coconut water", "Green tea",
                     "Sambar", "Coconut chutney"]
_BEVERAGES_GLOBAL = ["Coconut water", "Green tea"]


def _select_foods_for_client(client_data: dict) -> dict:
    """
    Select ~25–35 foods from NUTRITION_DB relevant to this client.
    Filtering by: diet type, location, goal, allergies, current diet.
    Returns a dict suitable for _build_nutrition_table().
    """
    diet_type  = (client_data.get("diet_type") or "non_vegetarian").lower()
    location   = ((client_data.get("state") or "") + " " + (client_data.get("city") or "")).lower()
    goal       = client_data.get("goal", "maintain")
    allergies  = [a.lower() for a in (client_data.get("food_allergies") or [])]
    current_diet = (client_data.get("current_diet_description") or "").lower()
    cuisines   = [c.lower() for c in (client_data.get("cuisine_preference") or [])]

    # Determine region
    indian_keywords = ["india", "chennai", "mumbai", "delhi", "bangalore", "hyderabad", "kolkata",
                       "pune", "kerala", "tamil", "telangana", "karnataka", "gujarat", "rajasthan",
                       "maharashtra", "bengal", "andhra", "assam", "odisha", "bihar", "punjab"]
    western_keywords = ["usa", "uk", "united states", "united kingdom", "australia", "canada",
                        "europe", "germany", "france", "italy", "spain", "london", "new york",
                        "sydney", "toronto", "western"]
    mid_east_keywords = ["uae", "dubai", "saudi", "qatar", "kuwait", "bahrain", "oman", "arab",
                         "middle east", "halal"]

    is_indian  = any(kw in location for kw in indian_keywords)
    is_western = any(kw in location for kw in western_keywords)
    is_mideast = any(kw in location for kw in mid_east_keywords)

    # Check cuisine preferences too
    if not is_indian and any(c in cuisines for c in ["indian", "south indian", "north indian"]):
        is_indian = True
    if not is_western and any(c in cuisines for c in ["western", "mediterranean", "european"]):
        is_western = True

    # Default to Indian if no location signal (most common client base)
    if not is_indian and not is_western and not is_mideast:
        is_indian = True

    selected_keys: list[str] = []

    # ── Grains ──────────────────────────────────────────────────────────────
    if is_indian:
        selected_keys.extend(_GRAINS_INDIAN[:7])
    elif is_western:
        selected_keys.extend(_GRAINS_WESTERN[:5])
    else:
        selected_keys.extend(_GRAINS_GLOBAL[:5])

    # ── Proteins — strictly filtered by diet type ────────────────────────────
    if diet_type == "vegan":
        selected_keys.extend(_PROTEINS_VEGAN)
    elif diet_type in ("vegetarian", "jain"):
        selected_keys.extend(_PROTEINS_VEG)
    elif diet_type == "eggetarian":
        selected_keys.extend(_PROTEINS_VEG)
        selected_keys.extend(_PROTEINS_EGG)
    elif diet_type == "pescatarian":
        selected_keys.extend(_PROTEINS_VEG[:4])
        selected_keys.extend(_PROTEINS_EGG)
        selected_keys.extend(_PROTEINS_FISH)
    elif diet_type in ("halal",):
        selected_keys.extend(_PROTEINS_EGG)
        selected_keys.extend(_PROTEINS_MEAT[:2])   # no pork (halal)
        selected_keys.extend(_PROTEINS_FISH[:2])
        selected_keys.extend(_PROTEINS_DAIRY)
    else:  # non_vegetarian (default)
        selected_keys.extend(_PROTEINS_EGG)
        selected_keys.extend(_PROTEINS_MEAT)
        selected_keys.extend(_PROTEINS_FISH[:2])
        selected_keys.extend(_PROTEINS_DAIRY[:3])
        if is_indian:
            selected_keys.extend(_PROTEINS_VEG[6:9])  # some dal for Indian non-veg

    # High-protein goal: add whey if not vegan
    if goal in ("gain_muscle", "sports_nutrition") and diet_type != "vegan":
        if "Whey protein" not in selected_keys:
            selected_keys.append("Whey protein")

    # ── Vegetables ────────────────────────────────────────────────────────────
    if is_indian:
        selected_keys.extend(_VEGS_INDIAN)
    else:
        selected_keys.extend(_VEGS_GLOBAL)

    # ── Fruits ────────────────────────────────────────────────────────────────
    if is_indian or is_mideast:
        selected_keys.extend(_FRUITS_TROPICAL[:5])
    else:
        selected_keys.extend(_FRUITS_GLOBAL)

    # ── Fats & Oils ───────────────────────────────────────────────────────────
    if is_indian:
        selected_keys.extend(_OILS_INDIAN)
    else:
        selected_keys.extend(_OILS_GLOBAL)

    # ── Nuts & Seeds — goal-tuned ─────────────────────────────────────────────
    if goal in ("gain_muscle", "sports_nutrition"):
        selected_keys.extend(["Almonds", "Peanuts", "Walnuts"])
    elif goal == "lose_weight":
        selected_keys.extend(["Almonds", "Flaxseeds", "Chia seeds"])
    else:
        selected_keys.extend(["Almonds", "Walnuts", "Flaxseeds"])

    # ── Beverages ─────────────────────────────────────────────────────────────
    if is_indian:
        selected_keys.extend(_BEVERAGES_INDIAN)   # include sambar + coconut chutney
    else:
        selected_keys.extend(_BEVERAGES_GLOBAL)

    # ── Scan current diet for mentioned foods — always include what they eat ──
    current_words = set(current_diet.split())
    for food_key in NUTRITION_DB:
        food_lower = food_key.lower()
        # Check if any word from current diet appears in this food name
        for word in current_words:
            if len(word) >= 4 and word in food_lower:
                if food_key not in selected_keys:
                    selected_keys.append(food_key)
                break

    # ── Apply allergy filter ──────────────────────────────────────────────────
    allergy_map = {
        "dairy": ["milk", "paneer", "curd", "yogurt", "ghee", "butter", "cheese", "lassi", "buttermilk", "whey", "cream", "khoa", "mawa", "rabri"],
        "gluten": ["bread", "roti", "wheat", "atta", "pasta", "upma", "semolina", "suji", "maida", "paratha", "puri", "chapati", "barley", "seitan"],
        "nuts": ["almonds", "cashews", "walnuts", "peanuts", "mixed nuts", "almond milk", "peanut butter", "groundnut", "groundnut oil", "peanut oil", "nut butter", "cashew butter", "walnut", "pistachio", "hazelnut", "pecan", "macadamia"],
        "tree_nuts": ["almonds", "cashews", "walnuts", "mixed nuts", "almond milk", "cashew butter", "walnut", "pistachio", "hazelnut", "pecan", "macadamia"],
        "peanut": ["peanuts", "peanut butter", "groundnut", "groundnut oil", "peanut oil"],
        "egg": ["egg"],
        "fish": ["fish", "salmon", "tuna", "prawn", "shrimp", "crab", "lobster", "squid", "mackerel", "sardine", "anchovy", "hilsa", "rohu", "catla"],
        "shellfish": ["prawn", "shrimp", "crab", "lobster", "squid"],
        "soy": ["tofu", "soy", "soya", "edamame", "soy milk", "tempeh", "miso"],
        "sesame": ["sesame", "til", "tahini", "sesame oil"],
    }
    for allergy in allergies:
        for allergen_key, blocked_words in allergy_map.items():
            if allergen_key in allergy or allergy in allergen_key:
                selected_keys = [
                    k for k in selected_keys
                    if not any(bw in k.lower() for bw in blocked_words)
                ]

    # ── De-duplicate while preserving order ───────────────────────────────────
    seen: set[str] = set()
    deduped: list[str] = []
    for k in selected_keys:
        if k in NUTRITION_DB and k not in seen:
            seen.add(k)
            deduped.append(k)

    log.info(f"Food selection: {len(deduped)} foods selected for {diet_type} / {location.strip() or 'India'}")
    return {k: NUTRITION_DB[k] for k in deduped}


# ── Python-side macro validator (no GPT call needed for small adjustments) ──────────
# Adjusts quantities of grain/oil/protein rows directly in the markdown text.
# Only falls back to GPT correction if the adjustment is too large.

_GRAIN_KEYWORDS  = {"rice", "oats", "roti", "bread", "pasta", "quinoa", "poha", "upma", "idli", "dosa"}
_OIL_KEYWORDS    = {"ghee", "oil", "butter"}
_PROTEIN_KEYWORDS = {"chicken", "fish", "egg", "dal", "paneer", "tofu", "salmon", "tuna", "prawn",
                     "curd", "yogurt", "whey", "rajma", "chickpeas", "chana", "moong", "masoor"}

_ROW_RE = re.compile(
    # Accepts both 7-col rows (no Alternative) and 8-col rows.
    # Groups: 1=Meal  2=Ingredient  3=Qty  4=kcal  5=Protein  6=Carbs  7=Fat  8=Alternative(opt)
    r"^\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)\|([^|]*)(?:\|([^|]*))?\|",
)
_QTY_RE = re.compile(r"(\d+\.?\d*)")


def _is_total_row(m) -> tuple[bool, bool]:
    """Return (is_meal_total, is_day_total). Checks both cell 1 and cell 2 since
    GPT writes '| **Meal Total** | | | ...' so the label is in group(1), not group(2)."""
    combined = (_NUM_RE.sub("", m.group(1)) + " " + _NUM_RE.sub("", m.group(2))).strip().lower()
    return "meal total" in combined, "day total" in combined


_DAY_TOTAL_LINE_RE = re.compile(r"^\|[^|]*\*?[Dd]ay\s+[Tt]otal\*?[^|]*\|", re.I)
_MEAL_TOTAL_LINE_RE = re.compile(r"^\|[^|]*\*?[Mm]eal\s+[Tt]otal\*?[^|]*\|", re.I)


def _normalize_day_to_target(day_block: str, target_kcal: int, food_db: dict) -> str:
    """
    Guaranteed calorie correction for one day section.

    Algorithm:
      Pass 1 — sum actual ingredient kcal from all 8-column rows (skip total rows).
      Pass 2 — scale every ingredient row by (target / actual).
      Pass 3 — recompute Meal Total and Day Total rows from the scaled sums.
      Fallback — if no Day Total row existed, append one; replace any unparsed
                 Day Total rows via regex so the value is never left stale.

    After this call _parse_day_totals() will always read ≈ target_kcal.
    Scale is capped at 0.5×–2.5× to keep portions realistic.
    """
    lines = day_block.split("\n")

    def _fv(s: str) -> float:
        # Extract the first number found (handles ~107, **107**, "107 kcal", etc.)
        m = re.search(r'(\d+\.?\d*)', s.replace(',', ''))
        return float(m.group(1)) if m else 0.0

    # ── Pass 1: sum ingredient kcal ──────────────────────────────────────────
    actual_kcal = 0.0
    for line in lines:
        m = _ROW_RE.match(line)
        if not m:
            continue
        is_mt, is_dt = _is_total_row(m)
        if is_mt or is_dt:
            continue
        actual_kcal += _fv(m.group(4))

    if actual_kcal <= 0:
        log.warning("_normalize_day_to_target: no parseable ingredient rows found — block unchanged")
        return day_block

    scale = target_kcal / actual_kcal
    scale = max(0.5, min(2.5, scale))  # keep portions realistic

    # ── Pass 2: scale ingredient rows ────────────────────────────────────────
    scaled: list[str] = []
    for line in lines:
        m = _ROW_RE.match(line)
        if not m:
            scaled.append(line)
            continue
        is_mt, is_dt = _is_total_row(m)
        if is_mt or is_dt:
            scaled.append(line)   # placeholder — replaced in pass 3
            continue
        scaled.append(_adjust_qty_in_row(line, scale, food_db))

    # ── Pass 3: recompute totals from scaled ingredient values ───────────────
    result: list[str] = []
    day_k = day_p = day_c = day_f = 0.0
    meal_k = meal_p = meal_c = meal_f = 0.0
    dt_written = False

    for line in scaled:
        # Try _ROW_RE match first (standard 8-col rows)
        m = _ROW_RE.match(line)
        if m:
            is_mt, is_dt = _is_total_row(m)
            if is_mt:
                if meal_k > 0:
                    result.append(
                        f"| **Meal Total** | | | **{round(meal_k)}** | "
                        f"**{round(meal_p, 1)}** | **{round(meal_c, 1)}** | **{round(meal_f, 1)}** | |"
                    )
                else:
                    result.append(line)
                meal_k = meal_p = meal_c = meal_f = 0.0
                continue
            elif is_dt:
                result.append(
                    f"| **Day Total** | | | **{round(day_k)}** | "
                    f"**{round(day_p, 1)}** | **{round(day_c, 1)}** | **{round(day_f, 1)}** | |"
                )
                dt_written = True
                continue
            else:
                k = _fv(m.group(4)); p = _fv(m.group(5))
                c = _fv(m.group(6)); f = _fv(m.group(7))
                meal_k += k; meal_p += p; meal_c += c; meal_f += f
                day_k  += k; day_p  += p; day_c  += c; day_f  += f
                result.append(line)
                continue

        # Fallback: line didn't match _ROW_RE — check via regex for total rows
        if _DAY_TOTAL_LINE_RE.match(line):
            # Replace stale Day Total with computed value (handles non-standard column counts)
            result.append(
                f"| **Day Total** | | | **{round(day_k)}** | "
                f"**{round(day_p, 1)}** | **{round(day_c, 1)}** | **{round(day_f, 1)}** | |"
            )
            dt_written = True
        elif _MEAL_TOTAL_LINE_RE.match(line):
            if meal_k > 0:
                result.append(
                    f"| **Meal Total** | | | **{round(meal_k)}** | "
                    f"**{round(meal_p, 1)}** | **{round(meal_c, 1)}** | **{round(meal_f, 1)}** | |"
                )
                meal_k = meal_p = meal_c = meal_f = 0.0
            else:
                result.append(line)
        else:
            result.append(line)

    # ── Fallback: append Day Total if GPT never wrote one ────────────────────
    if not dt_written and day_k > 0:
        result.append(
            f"| **Day Total** | | | **{round(day_k)}** | "
            f"**{round(day_p, 1)}** | **{round(day_c, 1)}** | **{round(day_f, 1)}** | |"
        )

    log.info(
        f"_normalize_day_to_target: {actual_kcal:.0f} → {day_k:.0f} kcal "
        f"(target {target_kcal}, scale ×{scale:.2f})"
    )
    return "\n".join(result)


def _adjust_qty_in_row(row_line: str, factor: float, food_db: dict) -> str:
    """
    Scale the quantity in an ingredient row by `factor` and recompute macros.
    Returns the updated row line, or the original if it can't be parsed.
    """
    m = _ROW_RE.match(row_line)
    if not m:
        return row_line

    meal_cell = m.group(1).strip()
    ingredient = m.group(2).strip().lstrip("*").rstrip("*").strip()
    qty_cell   = m.group(3).strip()
    notes_cell = (m.group(8) or "").strip()

    # Skip total rows
    if any(t in ingredient.lower() for t in ("meal total", "day total")):
        return row_line

    # Find qty number
    qty_match = _QTY_RE.search(qty_cell)
    if not qty_match:
        return row_line
    old_qty = float(qty_match.group(1))
    new_qty = round(old_qty * factor, 1)

    # Always scale kcal and macros proportionally from GPT's original values.
    # Using DB values for kcal/macros breaks the proportionality guarantee because
    # GPT may have used different per-gram values than what the DB stores.
    # Proportional scaling ensures: sum(new_kcal_i) = actual_kcal × factor = target_kcal.
    def _scale_cell(cell: str) -> str:
        m2 = _QTY_RE.search(cell)
        return str(round(float(m2.group(1)) * factor, 1)) if m2 else cell.strip()

    new_kcal_str = _scale_cell(m.group(4))
    new_p_str    = _scale_cell(m.group(5))
    new_c_str    = _scale_cell(m.group(6))
    new_f_str    = _scale_cell(m.group(7))

    new_qty_cell = qty_cell.replace(qty_match.group(1), str(int(new_qty) if new_qty == int(new_qty) else new_qty), 1)
    return f"| {meal_cell} | {ingredient} | {new_qty_cell} | {new_kcal_str} | {new_p_str} | {new_c_str} | {new_f_str} | {notes_cell} |"


def _python_adjust_day(day_block: str, cal_diff: float, food_db: dict) -> str:
    """
    Adjust a single day's food quantities purely in Python.
    cal_diff > 0 means we need to ADD calories; < 0 means REDUCE.
    Adjusts grains first (~60%), then oils (~25%), then protein (~15%).
    Returns the adjusted day block.
    """
    if abs(cal_diff) < 30:
        return day_block  # too small to bother

    lines = day_block.split("\n")
    grain_indices:   list[int] = []
    oil_indices:     list[int] = []
    protein_indices: list[int] = []

    for i, line in enumerate(lines):
        m = _ROW_RE.match(line)
        if not m:
            continue
        ing = m.group(2).strip().lower()
        if any(t in ingredient.lower() for t in ("meal total", "day total") for ingredient in [ing]):
            continue
        if any(kw in ing for kw in _GRAIN_KEYWORDS):
            grain_indices.append(i)
        elif any(kw in ing for kw in _OIL_KEYWORDS):
            oil_indices.append(i)
        elif any(kw in ing for kw in _PROTEIN_KEYWORDS):
            protein_indices.append(i)

    remaining = cal_diff

    def _apply_group(indices: list[int], share: float) -> None:
        nonlocal remaining
        if not indices:
            return
        portion = remaining * share / len(indices)
        for idx in indices:
            line = lines[idx]
            m2 = _ROW_RE.match(line)
            if not m2:
                continue
            ing  = m2.group(2).strip()
            qty_m = _QTY_RE.search(m2.group(3))
            if not qty_m:
                continue
            qty = float(qty_m.group(1))
            # Find kcal/100g for this food
            kcal_per_100 = 130.0  # default to rice if unknown
            for fk, fv in food_db.items():
                if any(w in ing.lower() for w in fk.lower().split()[:2]):
                    kcal_per_100 = fv[0]
                    break
            if kcal_per_100 == 0:
                continue
            # How many grams to add/remove to get `portion` kcal change?
            delta_g = (portion / kcal_per_100) * 100
            factor  = (qty + delta_g) / qty if qty > 0 else 1.0
            # Cap adjustment to ±80% (large gaps like +700 kcal need aggressive scaling)
            factor = max(0.2, min(1.8, factor))
            lines[idx] = _adjust_qty_in_row(line, factor, food_db)
            remaining -= portion

    _apply_group(grain_indices,   0.60)
    _apply_group(oil_indices,     0.25)
    _apply_group(protein_indices, 0.15)

    # Rebuild Meal Total and Day Total rows
    # (We leave them as-is here — the GPT correction pass will recalculate them if still off)
    return "\n".join(lines)


# ── Post-generation verification + correction ────────────────────────────────

_DAY_RE  = re.compile(r"^###[^a-zA-Z]*(monday|tuesday|wednesday|thursday|friday|saturday|sunday)", re.I)
_SEC_RE  = re.compile(r"^##\s+(?!#)", re.I)   # ## but not ###
_NUM_RE  = re.compile(r"\*+")


def _parse_day_totals(plan: str) -> dict[str, tuple]:
    """
    Extract Day Total rows from plan markdown.
    Returns {day_title: (kcal, protein, carbs, fat)}.

    Handles multiple column layouts GPT might use:
      8-col: | Day Total | | | kcal | P | C | F | Notes |  → numeric at [3,4,5,6]
      6-col: | Day Total | kcal | P | C | F | Notes |       → numeric at [1,2,3,4]
      5-col: | Day Total | kcal | P | C | F |               → numeric at [1,2,3,4]
    Searches for the first cell with a value >500 to locate kcal column.
    """
    days: dict[str, tuple] = {}
    current_day: str | None = None

    def _f(s: str) -> float:
        m = re.search(r'(\d+\.?\d*)', s.replace(',', ''))
        return float(m.group(1)) if m else 0.0

    for line in plan.split("\n"):
        m = _DAY_RE.match(line.strip())
        if m:
            current_day = m.group(1).title()
            continue

        if not current_day or "|" not in line:
            continue
        if not re.search(r"day\s*total", line, re.I):
            continue

        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) < 4:
            continue

        # Find kcal column: first numeric cell with value > 500
        kcal_idx = None
        for i, cell in enumerate(cells):
            v = _f(cell)
            if v > 500:
                kcal_idx = i
                break

        if kcal_idx is None:
            log.debug(f"Day Total row found but no kcal cell >500: {line[:80]}")
            continue

        # Expect protein, carbs, fat in the next 3 columns
        if kcal_idx + 3 >= len(cells):
            continue

        kcal    = _f(cells[kcal_idx])
        protein = _f(cells[kcal_idx + 1])
        carbs   = _f(cells[kcal_idx + 2])
        fat     = _f(cells[kcal_idx + 3])

        if kcal > 500:
            days[current_day] = (kcal, protein, carbs, fat)
            log.debug(f"Parsed {current_day}: {kcal:.0f} kcal / {protein:.1f}P / {carbs:.1f}C / {fat:.1f}F")

    return days


def _apply_day_corrections(original: str, corrections: str, days_to_fix: list[str]) -> str:
    """
    Splice corrected day sections from `corrections` back into `original`.
    Each corrected section starts at ### DAY and ends at the next ### or ##.
    """
    days_upper = {d.upper() for d in days_to_fix}

    # Extract corrected day sections from the correction response
    corrected: dict[str, list[str]] = {}
    curr: str | None = None
    for line in corrections.split("\n"):
        m = _DAY_RE.match(line.strip())
        if m:
            day = m.group(1).upper()
            if day in days_upper:
                curr = day
                corrected[curr] = [line]
            else:
                curr = None
        elif curr:
            if _SEC_RE.match(line.strip()):
                curr = None
            else:
                corrected[curr].append(line)

    if not corrected:
        log.warning("Correction call returned no parseable day sections — keeping original")
        return original

    # Rebuild original, replacing the targeted day sections
    result: list[str] = []
    skip = False

    for line in original.split("\n"):
        m = _DAY_RE.match(line.strip())
        if m:
            day = m.group(1).upper()
            if day in corrected:
                result.extend(corrected[day])
                skip = True
            else:
                skip = False
                result.append(line)
        elif skip:
            # End of skipped section when we hit the next day or ## section
            if _DAY_RE.match(line.strip()) or _SEC_RE.match(line.strip()):
                skip = False
                result.append(line)
            # else: discard — this line belongs to the replaced day
        else:
            result.append(line)

    log.info(f"Applied corrections for days: {list(corrected.keys())}")
    return "\n".join(result)


def _find_off_days(plan: str, cal: int, protein: int, carbs: int, fat: int,
                   bmr: int | None = None) -> list[dict]:
    """Parse Day Total rows and return days that exceed allowed tolerances."""
    totals = _parse_day_totals(plan)
    if not totals:
        return []
    result = []
    for day, (act_kcal, act_p, act_c, act_f) in totals.items():
        issues = []
        # Use max(cal, bmr) as effective floor — ensures we never target below BMR
        effective_cal = max(cal, bmr) if bmr else cal
        kcal_pct = abs(act_kcal - effective_cal) / effective_cal * 100
        if act_kcal < effective_cal * 0.97 or act_kcal > effective_cal * 1.03:
            issues.append(f"calories_out_of_range ({act_kcal:.0f} vs {effective_cal})")
        if act_p < protein - 10:
            issues.append(f"protein_low ({act_p:.1f}g < {protein - 10}g)")
        if act_c < carbs - 25:
            issues.append(f"carbs_low ({act_c:.1f}g < {carbs - 25}g)")
        if act_f > fat + 10:
            issues.append(f"fat_high ({act_f:.1f}g > {fat + 10}g)")
        if issues:
            result.append({
                "day":    day,
                "actual": (act_kcal, act_p, act_c, act_f),
                "diff":   (act_kcal - effective_cal, act_p - protein, act_c - carbs, act_f - fat),
                "pct":    kcal_pct,
                "issues": issues,
            })
    return result


def _extract_day_sections(plan: str) -> dict[str, list[str]]:
    """Split plan into day sections {day_title: [lines]}."""
    sections: dict[str, list[str]] = {}
    current: str | None = None
    for line in plan.split("\n"):
        m = _DAY_RE.match(line.strip())
        if m:
            current = m.group(1).title()
            sections[current] = [line]
        elif current:
            if _SEC_RE.match(line.strip()) and not _DAY_RE.match(line.strip()):
                current = None
            else:
                sections[current].append(line)
    return sections


def _splice_day_sections(plan: str, sections: dict[str, list[str]]) -> str:
    """Reconstruct plan replacing specified day sections."""
    result: list[str] = []
    in_day: str | None = None
    written: set[str] = set()

    for line in plan.split("\n"):
        m = _DAY_RE.match(line.strip())
        if m:
            in_day = m.group(1).title()
            if in_day in sections and in_day not in written:
                result.extend(sections[in_day])
                written.add(in_day)
            else:
                in_day = None
                result.append(line)
        elif in_day and in_day in written:
            if _SEC_RE.match(line.strip()) or _DAY_RE.match(line.strip()):
                in_day = None
                result.append(line)
        else:
            result.append(line)

    return "\n".join(result)


def _recalculate_weekly_summary(plan: str, cal: int, protein: int, carbs: int, fat: int) -> str:
    """
    Parse all 7 Day Total rows from the validated plan, compute exact averages,
    and replace GPT's weekly summary table with Python-calculated values.
    """
    day_totals = _parse_day_totals(plan)
    if len(day_totals) < 7:
        log.warning(f"Only {len(day_totals)}/7 day totals parsed — skipping weekly summary recalc")
        return plan

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    rows = []
    sum_kcal = sum_p = sum_c = sum_f = 0.0

    for day in day_order:
        if day in day_totals:
            k, p, c, f = day_totals[day]
            sum_kcal += k; sum_p += p; sum_c += c; sum_f += f
            rows.append(f"| {day} | {k:.0f} | {p:.1f} | {c:.1f} | {f:.1f} |")
        else:
            rows.append(f"| {day} | — | — | — | — |")

    n = len([d for d in day_order if d in day_totals])
    avg_k = sum_kcal / n if n else 0
    avg_p = sum_p   / n if n else 0
    avg_c = sum_c   / n if n else 0
    avg_f = sum_f   / n if n else 0

    new_summary = (
        "| Day | kcal | Protein (g) | Carbs (g) | Fat (g) |\n"
        "|-----|------|-------------|-----------|--------|\n"
        + "\n".join(rows)
        + f"\n| **Average** | **{avg_k:.0f}** | **{avg_p:.1f}** | **{avg_c:.1f}** | **{avg_f:.1f}** |"
    )

    # Find and replace the existing weekly summary table in the plan
    _WEEKLY_TABLE_RE = re.compile(
        r"\| *Day *\| *[kK]cal[^\n]*\n\|[-| ]+\n(?:\|[^\n]+\n)+"
        r"(?:\| *\*?\*?Average\*?\*?[^\n]+\n)?",
        re.MULTILINE,
    )
    replaced, n_subs = _WEEKLY_TABLE_RE.subn(new_summary + "\n", plan, count=1)
    if n_subs:
        log.info(f"Weekly summary recalculated — avg: {avg_k:.0f} kcal / {avg_p:.1f}g P / {avg_c:.1f}g C / {avg_f:.1f}g F")
        return replaced

    log.warning("Weekly summary table not found in plan — appending recalculated values")
    return plan


def _inject_verification_note(plan: str, cal: int, protein: int, carbs: int, fat: int) -> str:
    """
    Replace SECTION D verification note with Python-computed actual Day Total results.
    Shows each day's real kcal vs target, and whether macros are within tolerance.
    """
    day_totals = _parse_day_totals(plan)
    if not day_totals:
        return plan

    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    lines = []
    all_pass = True
    for day in day_order:
        if day not in day_totals:
            continue
        k, p, c, f = day_totals[day]
        diff = k - cal
        pct  = abs(diff) / cal * 100
        ok   = pct <= 3.0 and abs(p - protein) <= 10 and abs(c - carbs) <= 25 and abs(f - fat) <= 10
        if not ok:
            all_pass = False
        status = "✓" if ok else "⚠"
        lines.append(
            f"{status} {day}: {k:.0f} kcal (target {cal}, diff {diff:+.0f}) | "
            f"P {p:.1f}g (±{abs(p-protein):.1f}) | C {c:.1f}g (±{abs(c-carbs):.1f}) | F {f:.1f}g (±{abs(f-fat):.1f})"
        )

    if all_pass:
        summary = f"All 7 days verified — totals within ±3% of {cal} kcal and macro tolerances."
    else:
        n_fail = sum(1 for d in day_order if d in day_totals and (
            abs(day_totals[d][0] - cal) / cal * 100 > 3.0
        ))
        summary = f"{n_fail} day(s) outside ±2% tolerance — see details below."

    verification_block = f"{summary}\n\n" + "\n".join(lines)

    # Replace SECTION D content in the plan
    _SECTION_D_RE = re.compile(
        r"(SECTION D[^\n]*\n)(.*?)(?=\n---|\n##\s|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    replaced, n = _SECTION_D_RE.subn(r"\1" + verification_block + "\n", plan, count=1)
    if n:
        log.info(f"Verification note injected — {summary[:60]}")
        return replaced
    return plan


def _round_quantities_to_5g(plan: str) -> str:
    """
    Round all ingredient quantities to the nearest 5g and scale macros proportionally.
    Skips Meal Total / Day Total rows (those are recalculated by enforcement).
    Skips non-gram quantities (e.g. "1 tsp", "2 cups").
    """
    _QTY_GRAM_RE = re.compile(r"(\d+(?:\.\d+)?)\s*g\b")

    def _round5(val: float) -> int:
        return int(round(val / 5) * 5)

    def _process_row(line: str) -> str:
        m = _ROW_RE.match(line)
        if not m:
            return line

        ingredient = m.group(2).strip().lstrip("*").rstrip("*").strip()
        if any(t in ingredient.lower() for t in ("meal total", "day total")):
            return line

        qty_cell = m.group(3).strip()
        qty_match = _QTY_GRAM_RE.search(qty_cell)
        if not qty_match:
            return line  # non-gram qty — leave as is

        old_qty = float(qty_match.group(1))
        if old_qty <= 0:
            return line
        new_qty = _round5(old_qty)
        if new_qty <= 0:
            new_qty = 5
        factor = new_qty / old_qty

        def _scale_cell(cell: str) -> str:
            m2 = re.search(r"(\d+(?:\.\d+)?)", cell)
            if not m2:
                return cell.strip()
            scaled = float(m2.group(1)) * factor
            # Round macros to 1 decimal
            return cell.strip().replace(m2.group(1), str(round(scaled, 1)), 1)

        meal_cell = m.group(1).strip()
        notes_cell = (m.group(8) or "").strip()
        new_qty_cell = qty_cell.replace(qty_match.group(1), str(new_qty), 1)
        new_kcal = _scale_cell(m.group(4))
        new_p    = _scale_cell(m.group(5))
        new_c    = _scale_cell(m.group(6))
        new_f    = _scale_cell(m.group(7))

        return f"| {meal_cell} | {ingredient} | {new_qty_cell} | {new_kcal} | {new_p} | {new_c} | {new_f} | {notes_cell} |"

    return "\n".join(_process_row(line) for line in plan.split("\n"))


async def _verify_and_correct_plan(
    plan: str,
    targets: "CalorieTargets",
    nutrition_table: str,
    food_db: dict | None = None,
) -> str:
    """
    Validation loop — runs until all days pass or MAX_ITERATIONS reached.
    Iteration 1: Python quantity adjustments (no GPT call)
    Iteration 2+: GPT correction for days still off
    Final step: Python recalculates weekly summary from validated Day Totals.
    """
    MAX_ITERATIONS = 3
    cal     = int(targets.calorie_target)
    protein = int(targets.protein_g)
    carbs   = int(targets.carb_g)
    fat     = int(targets.fat_g)
    bmr     = int(targets.bmr)
    db      = food_db or NUTRITION_DB

    off_days = _find_off_days(plan, cal, protein, carbs, fat, bmr=bmr)
    if not off_days:
        log.info("Initial validation passed — skipping correction loop")
    else:
        for iteration in range(1, MAX_ITERATIONS + 1):
            off_days = _find_off_days(plan, cal, protein, carbs, fat, bmr=bmr)
            if not off_days:
                log.info(f"Validation loop complete after {iteration - 1} iteration(s) — all days pass")
                break

            log.info(f"Iteration {iteration}/{MAX_ITERATIONS}: {len(off_days)} day(s) off — "
                     f"{[d['day'] + ' (' + ', '.join(d['issues']) + ')' for d in off_days]}")

            if iteration == 1:
                # Python-only pass: targeted adjustment (grains/oils/protein) THEN
                # recompute Day Totals so the next _find_off_days() reads updated values.
                sections = _extract_day_sections(plan)
                for od in off_days:
                    day = od["day"]
                    if day in sections:
                        block    = "\n".join(sections[day])
                        cal_diff = -(od["diff"][0])   # positive = need to ADD calories
                        block    = _python_adjust_day(block, cal_diff, db)
                        # Recompute Day Total so next iteration sees the corrected value
                        block    = _normalize_day_to_target(block, int(max(cal, bmr)), db)
                        sections[day] = block.split("\n")
                plan = _splice_day_sections(plan, sections)

            else:
                # GPT correction pass for remaining off days
                off_lines = []
                for od in off_days:
                    dk, dp, dc, df = od["diff"]
                    direction = "REDUCE" if dk > 0 else "INCREASE"
                    off_lines.append(
                        f"- {od['day']}: actual {od['actual'][0]:.0f} kcal (target {cal}). "
                        f"Difference: {dk:+.0f} kcal / {dp:+.1f}g P / {dc:+.1f}g C / {df:+.1f}g F. "
                        f"Issues: {'; '.join(od['issues'])}. Action: {direction} food quantities."
                    )

                correction_prompt = f"""The meal plan has Day Total errors for these days:

{chr(10).join(off_lines)}

TARGETS: {cal} kcal | {protein}g protein | {carbs}g carbs | {fat}g fat
TOLERANCES: calories ±3% | protein ±10g | carbs ±25g | fat ±10g

CORRECTION RULES:
1. Adjust GRAINS first (rice/oats/roti/bread) — ±30–80g
2. Then OILS/GHEE — ±3–8g
3. Then PROTEIN portions — ±30–50g
4. Do NOT change food selection — adjust quantities only
5. Recalculate EACH modified row: kcal = (qty ÷ 100) × table_kcal (same for P/C/F)
6. Update Meal Total and Day Total rows with new sums

NUTRITION REFERENCE TABLE:
{nutrition_table}

Return ONLY the corrected day sections (### MONDAY etc.) for the days listed above.
Format: | Meal | Ingredient | Qty (g/ml) | kcal | Protein (g) | Carbs (g) | Fat (g) | Local / Affordable Alternative |

ORIGINAL PLAN:
{plan}"""

                try:
                    correction = await _gpt_call(correction_prompt, max_tokens=4000)
                    plan = _apply_day_corrections(plan, correction, [d["day"] for d in off_days])
                except Exception as e:
                    log.error(f"GPT correction (iteration {iteration}) failed: {e}")
                    break

    # Final validation report
    final_off = _find_off_days(plan, cal, protein, carbs, fat, bmr=bmr)
    if final_off:
        log.warning(f"Validation ended with {len(final_off)} day(s) still off: "
                    f"{[d['day'] for d in final_off]}")
    else:
        log.info("All 7 days validated — all within tolerance")

    # ── Calorie target enforcement (UNCONDITIONAL — runs on all 7 days) ────────
    # Do NOT rely on _parse_day_totals() to decide which days to fix.
    # Instead: iterate all 7 day names, extract each section, and run
    # _normalize_day_to_target() on every one.
    #
    # Why unconditional:
    #   • _parse_day_totals() might miss a day if its Day Total row is malformed
    #   • Days that already hit the target get scale≈1.0 → no change
    #   • Days that are off get scaled to exactly target_kcal
    # This is the GUARANTEED pass — no day can leave with wrong calories.
    effective_cal = max(cal, bmr)
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    sections_all = _extract_day_sections(plan)

    for day in day_order:
        if day not in sections_all:
            log.warning(f"Calorie enforcement: '{day}' section not found in plan")
            continue
        block = "\n".join(sections_all[day])
        sections_all[day] = _normalize_day_to_target(block, effective_cal, db).split("\n")

    plan = _splice_day_sections(plan, sections_all)
    log.info(f"Calorie enforcement complete — all days normalised to {effective_cal} kcal")

    # Round all ingredient quantities to nearest 5g (professional appearance)
    plan = _round_quantities_to_5g(plan)
    log.info("Ingredient quantities rounded to nearest 5g")

    # Recalculate weekly summary
    plan = _recalculate_weekly_summary(plan, cal, protein, carbs, fat)

    # Strip any SECTION D / VERIFICATION NOTE block — clients must never see it
    _VN_RE = re.compile(
        r"\n*(?:---\s*\n+)?(?:SECTION\s+D\b[^\n]*|VERIFICATION\s+NOTE[^\n]*).*?(?=\n---\s*\n|\n##\s|\Z)",
        re.DOTALL | re.IGNORECASE,
    )
    plan = _VN_RE.sub("", plan)

    return plan


# ── Exercise Templates ──────────────────────────────────────────────────────────

EXERCISE_SCHEDULE = {
    "yoga": [
        ("Monday",    "Yoga — Surya Namaskar (10 rounds) + Trikonasana + Virabhadrasana", "45 min", "Full-body activation, burns ~180 kcal, improves flexibility"),
        ("Tuesday",   "Yoga — Naukasana + Setu Bandhasana + Bhujangasana + Balasana",    "40 min", "Core strength, spinal health, hip flexibility"),
        ("Wednesday", "Yoga — Adho Mukha Svanasana + Utkatasana + Vrksasana",             "40 min", "Balance, leg strength, shoulder mobility"),
        ("Thursday",  "Yoga — Paschimottanasana + Ardha Matsyendrasana + Dhanurasana",   "40 min", "Deep stretch, spinal rotation, hamstring release"),
        ("Friday",    "Yoga — Surya Namaskar (12 rounds) + Sarvangasana + Kapalbhati",   "50 min", "Cardio + inversion, stimulates thyroid and digestion"),
        ("Saturday",  "Yin Yoga + Pranayama (Anulom Vilom + Bhramari) — recovery",       "35 min", "Deep fascia release, lowers cortisol, promotes sleep quality"),
        ("Sunday",    "Rest — 15 min gentle stretching only",                             "15 min", "Muscle recovery and nervous system reset"),
    ],
    "gym": [
        ("Monday",    "Gym — Chest + Triceps (Bench Press, Incline DB, Cable Pushdown)",  "50 min", "Upper body push strength, burns ~300 kcal"),
        ("Tuesday",   "Gym — Back + Biceps (Lat Pulldown, Seated Row, DB Curl)",          "50 min", "Upper body pull strength, posture improvement"),
        ("Wednesday", "Gym — Legs (Squat, Leg Press, Leg Curl, Calf Raise)",              "55 min", "Largest muscle groups — highest calorie burn ~400 kcal"),
        ("Thursday",  "Gym — Shoulders + Core (OHP, Lateral Raise, Plank, Cable Crunch)", "45 min", "Shoulder stability, core endurance"),
        ("Friday",    "Gym — Full Body Compound (Deadlift, Pull-ups, Dips, Farmer Carry)","55 min", "Maximal muscle activation, testosterone boost"),
        ("Saturday",  "Light Cardio — 30 min treadmill or cycling (Zone 2, 120–140 bpm)","30 min", "Active recovery, fat oxidation, heart health"),
        ("Sunday",    "Rest — full recovery",                                              "—",      "Muscle protein synthesis peaks during rest"),
    ],
    "cardio": [
        ("Monday",    "Brisk Walk / Light Jog — maintain 120–140 bpm (Zone 2)",          "35 min", "Fat-burning zone, improves cardiovascular base"),
        ("Tuesday",   "Interval Run — 2 min jog + 1 min walk × 10 rounds",               "30 min", "Boosts metabolism for 24 hrs post-exercise"),
        ("Wednesday", "Cycling — moderate pace, outdoors or stationary bike",             "40 min", "Low-impact, high calorie burn ~250 kcal"),
        ("Thursday",  "Rest or 20 min gentle yoga — active recovery",                    "20 min", "Prevents overtraining, maintains flexibility"),
        ("Friday",    "Tempo Run — comfortable hard pace for 25 min continuous",          "35 min", "Improves aerobic threshold and endurance"),
        ("Saturday",  "Long Steady Walk — 6,000+ steps + 10 min stretching",             "50 min", "Mental reset, bone density, low-impact fat burn"),
        ("Sunday",    "Rest",                                                             "—",      "Full recovery day"),
    ],
    "hiit": [
        ("Monday",    "HIIT — Circuit A: Jump Squats + Mountain Climbers + Burpees (×3 rounds)", "35 min", "Burns 300–400 kcal, EPOC effect lasts 24+ hrs"),
        ("Tuesday",   "Rest or 20 min light yoga",                                               "20 min", "Recovery — HIIT requires 48h between sessions"),
        ("Wednesday", "HIIT — Circuit B: High Knees + Push-ups + Jumping Jacks + Dips (×3)",    "35 min", "Full-body conditioning, improves VO2 max"),
        ("Thursday",  "Rest or 30 min brisk walk",                                               "30 min", "Active recovery, reduces muscle soreness"),
        ("Friday",    "HIIT — Tabata: 20 sec max effort + 10 sec rest × 8 per exercise",         "35 min", "Peak metabolic conditioning, fat loss acceleration"),
        ("Saturday",  "30 min steady-state cardio (walk / cycle) + core work",                   "40 min", "Low-intensity complement to HIIT week"),
        ("Sunday",    "Rest — full recovery",                                                     "—",      "Essential for HIIT adaptation and muscle repair"),
    ],
    "home_workout": [
        ("Monday",    "Home — Push Day: Push-ups (4×15) + Pike Push-ups + Tricep Dips (chair)",   "40 min", "Upper body strength without equipment"),
        ("Tuesday",   "Home — Legs: Squats (4×20) + Reverse Lunges + Glute Bridge + Calf Raise",  "40 min", "Glute and quad activation, ~280 kcal burned"),
        ("Wednesday", "Home — Core: Plank (3×60s) + Crunches + Leg Raises + Superman Hold",       "35 min", "Deep core stability, lower back strength"),
        ("Thursday",  "Home Cardio — Jump rope 15 min OR 4,000 steps + stair climbs ×10",         "30 min", "Cardiovascular fitness, footwork coordination"),
        ("Friday",    "Home HIIT — 40s on / 20s off: Burpees, Squats, Push-ups, Climbers ×4",     "35 min", "Full-body burn, no equipment needed"),
        ("Saturday",  "Flexibility — 30 min full-body stretching (hamstrings, chest, shoulders)",   "30 min", "Prevents injury, improves joint mobility"),
        ("Sunday",    "Rest",                                                                       "—",      "Recovery and muscle growth"),
    ],
    "dance": [
        ("Monday",    "Dance Fitness — Bollywood / Zumba (full-body, high energy)",              "45 min", "Burns ~350 kcal, improves coordination and mood"),
        ("Tuesday",   "Dance — Footwork drills + rhythm exercises (Kathak tatkaar or Latin)",    "35 min", "Ankle strength, rhythm, calves, mental focus"),
        ("Wednesday", "Rest or 20 min light stretching",                                         "20 min", "Recovery between dance sessions"),
        ("Thursday",  "Dance Fitness — Contemporary / Hip-hop / freestyle session",              "45 min", "Creative full-body expression, ~300 kcal burned"),
        ("Friday",    "Dance Cardio Intervals — 30s intense + 15s slow × 20 rounds",            "35 min", "Metabolic conditioning, cardio endurance"),
        ("Saturday",  "Dance — Learn new choreography or style (30 min) + stretching",          "45 min", "Skill development, flexibility, low intensity"),
        ("Sunday",    "Rest + 20 min yoga or meditation",                                        "20 min", "Mind-body recovery, reduces cortisol"),
    ],
}


def _resolve_exercise_keys(client_data: dict) -> list:
    pref = client_data.get("exercise_preference", [])
    if isinstance(pref, str):
        pref = [pref] if pref else []

    if not pref:
        ex_type = (client_data.get("exercise_type", "") or "").lower()
        if "yoga" in ex_type:              pref = ["yoga"]
        elif "gym" in ex_type or "weight" in ex_type: pref = ["gym"]
        elif "run" in ex_type or "cardio" in ex_type: pref = ["cardio"]
        elif "hiit" in ex_type:            pref = ["hiit"]
        elif "dance" in ex_type:           pref = ["dance"]
        else:                              pref = ["home_workout"]

    key_map = {"yoga": "yoga", "gym": "gym", "cardio": "cardio",
               "hiit": "hiit", "home_workout": "home_workout", "dance": "dance"}
    keys = [key_map[p] for p in pref if p in key_map]
    return keys if keys else ["home_workout"]


def _build_exercise_block(client_data: dict) -> str:
    """
    Build a Mon–Sun exercise table string for the prompt.
    If multiple exercise types, alternate them across the week.
    """
    keys = _resolve_exercise_keys(client_data)
    label = " + ".join(k.replace("_", " ").title() for k in keys)

    freq_map = {
        "sedentary": "3 days/week", "lightly_active": "4 days/week",
        "moderately_active": "5 days/week", "very_active": "6 days/week", "athlete": "6 days/week"
    }
    freq = freq_map.get(client_data.get("activity_level", "sedentary"), "4 days/week")

    # If only one exercise type, use its schedule directly
    if len(keys) == 1:
        schedule = EXERCISE_SCHEDULE[keys[0]]
    else:
        # Interleave: alternate types across weekdays, keep Sun as rest
        schedules = [EXERCISE_SCHEDULE[k] for k in keys]
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        schedule = []
        active_days = [d for d in range(6)]  # Mon–Sat
        for i, day_idx in enumerate(active_days):
            src = schedules[i % len(schedules)]
            _, activity, duration, benefit = src[day_idx % len(src)]
            schedule.append((days[day_idx], activity, duration, benefit))
        # Sunday always rest
        schedule.append(("Sunday", "Rest — full recovery", "—", "Muscle recovery and nervous system reset"))

    lines = ["| Day | Activity | Duration | Benefit |", "|-----|----------|----------|---------|"]
    for day, activity, duration, benefit in schedule:
        lines.append(f"| {day} | {activity} | {duration} | {benefit} |")

    return f"Exercise type: {label} | Recommended frequency: {freq}\n\n" + "\n".join(lines)


SYSTEM_PROMPT = """You are NutriVeda AI, a professional nutrition planning system trained using MHB (Modern Health & Biology) certification material.

Your task is to generate scientifically correct, mathematically validated diet plans for clients anywhere in the world.

The plan must be culturally appropriate, nutritionally balanced, and aligned with the client's calorie and macronutrient requirements.

---

KNOWLEDGE SOURCE PRIORITY

Use nutrition information in the following order:

1. The NUTRITION REFERENCE TABLE provided in the user message — highest authority
2. Verified nutrition databases (USDA FoodData Central, IFCT, EuroFIR, national nutrition tables)
3. Scientific estimation using similar foods if data is unavailable

Never invent macronutrient values.

---

STEP 1 — METABOLISM VALUES

BMR and TDEE are pre-calculated by the system using Mifflin-St Jeor and provided in the client profile.
Use the provided values directly — do not recalculate.

---

STEP 2 — CALORIE TARGET

The daily calorie target is pre-calculated and provided. Use it.

---

STEP 3 — MACRONUTRIENT TARGETS

Macronutrient targets are pre-calculated and provided:
- Protein: 1.4–1.8 g per kg bodyweight
- Fat: 25–30% of total calories
- Carbohydrates: remaining calories after protein and fat

Use the provided targets. Do not recalculate.

---

STEP 4 — MEAL STRUCTURE

Per-meal calorie targets are provided in the client profile. Follow them as guides.
Meals per day and timing preferences are specified by the client.

---

STEP 5 — LOCAL FOOD ADAPTATION AND MEAL COMPOSITION

Select foods commonly available in the client's country and city.
Meals must reflect foods the client can easily obtain locally.
If the client has described their current diet, use those foods as the primary ingredients.

BALANCED MEAL RULE — every main meal (breakfast, lunch, dinner) must include:
  • 1 grain/starch   — rice, oats, roti, bread, quinoa, pasta, idli, etc.
  • 1–2 proteins     — chicken, eggs, fish, dal, paneer, tofu, legumes, yogurt, etc.
  • 1–2 vegetables   — spinach, broccoli, tomato, carrots, okra, cauliflower, etc.
  • 1 fat source     — ghee, oil, nuts, avocado, seeds (small quantity, 5–15g)

Snacks may be simpler (e.g. fruit + nuts, or yogurt alone).
This structure guarantees balanced macros and prevents nutritionally empty meals.

---

STEP 6 — INGREDIENT TABLE FORMAT (NON-NEGOTIABLE)

Every ingredient must appear in its own row. Never combine multiple foods in one cell.

Columns (8 total):
| Meal | Ingredient | Qty (g/ml) | kcal | Protein (g) | Carbs (g) | Fat (g) | Local / Affordable Alternative |

Rules:
- "Meal" column: show meal name only on the FIRST ingredient row; leave blank for subsequent rows
- After each meal's last ingredient: add "| **Meal Total** | | | **X** | **X** | **X** | **X** | |"
- After all meals of a day: add "| **Day Total** | | | **X** | **X** | **X** | **X** | |"
- Portions in GRAMS (g) and millilitres (ml) ONLY — "1 cup" or "1 bowl" is NEVER acceptable

---

STEP 7 — MACRO CALCULATION (NON-NEGOTIABLE)

The nutrition table uses per-gram values (kcal/g, P/g, C/g, F/g).
Calculation formula — one multiplication, no division needed:

  kcal    = qty_g × kcal_per_g
  protein = qty_g × P_per_g
  carbs   = qty_g × C_per_g
  fat     = qty_g × F_per_g

Example: White rice 200g → kcal = 200 × 1.30 = 260, P = 200 × 0.027 = 5.4g

Calculation process:
1. For each ingredient row: apply the formula above.
2. For each row: verify kcal ≈ (P×4) + (C×4) + (F×9) within ±5%. Fix if outside range.
3. Meal Total = arithmetic sum of its ingredient rows.
4. Day Total = sum of all Meal Totals.

NEVER copy calorie targets into the table. Only write values calculated from actual food quantities.

---

STEP 8 — AUTOMATIC MACRO CORRECTION

After computing Day Total, check against targets:

If calories are too low → increase grains (rice, oats, bread, potatoes).
If calories are too high → reduce grain portions first.
If protein is too low → add eggs, legumes, yogurt, tofu, fish, or whey protein.
If fat is too high → reduce oils, nuts, paneer, or fatty meats.

Allowed variance:
- Calories: ±3%
- Protein: ±10 g
- Carbs: ±25 g
- Fat: ±10 g

---

STEP 9 — WEEKLY PLAN

Generate a 7-day diet plan (Monday through Sunday).

VARIETY RULES (strict enforcement):
- No meal may repeat more than 2 times across all 7 days for any given meal slot (breakfast, lunch, dinner, snack).
- Protein sources must rotate across the week. Example: if chicken breast appears Monday lunch, do NOT use it again until Thursday at earliest. Alternate with fish, eggs, legumes, paneer, tofu, yogurt, etc.
- Breakfast must use at least 4 distinct recipes across 7 days (e.g., oats, eggs, smoothie, idli, paratha, upma, etc.).
- Dinner carb sources must alternate daily (rice → roti/bread → quinoa → sweet potato → rice, etc.).
- Snacks must vary — a different snack for each day of the week (7 distinct snack options).

MEAL TIMING RULES (precise, non-negotiable):
- Breakfast: 07:00–08:30 (adapt to client's specified timing if given)
- Mid-morning snack: 10:30–11:00
- Lunch: 12:30–13:30
- Evening snack: 16:00–16:30
- Dinner: 19:30–20:30
- If client specified meal_timings, use those exact times instead.
- Pre-workout meal: 60–90 minutes before training (if applicable).
- Post-workout meal: within 30–45 minutes after training (if applicable).
- Include the time in the Meal column header for each meal.

---

STEP 10 — WEEKLY SUMMARY TABLE

After all 7 days:
| Day | kcal | Protein (g) | Carbs (g) | Fat (g) |
Add an Average row at the bottom.

---

STEP 11 — EXERCISE PLAN

The exercise schedule is provided in the client profile. Include it as-is, but with these adaptations:

MEDICAL CONDITION EXERCISE ADAPTATIONS (apply strictly):
- Diabetes / High Blood Sugar: include post-meal 15-minute walks; avoid fasted high-intensity workouts; recommend resistance training 3×/week to improve insulin sensitivity.
- Hypertension / High BP: avoid heavy isometric exercises; focus on moderate-intensity cardio 30 min/day; no Valsalva maneuver (no breath-holding during lifts).
- PCOS: prioritize strength training + low-impact cardio (cycling, swimming, yoga); avoid chronic high-intensity cardio which can spike cortisol.
- Thyroid (Hypothyroid): resistance training to boost metabolism; avoid extreme caloric restriction with workouts; morning exercise preferred.
- Knee / Joint pain: replace squats with seated leg press or wall sits; replace running with cycling or swimming; no impact exercises.
- Back pain (lumbar): no deadlifts or heavy barbell squats; replace with cable rows, lat pulldowns, planks; focus on core stability.
- Heart conditions: keep heart rate under 70% of max HR; only light to moderate activity; mandatory warm-up and cool-down 10 min each.
- Pregnancy: only prenatal-safe exercises; walking, prenatal yoga, light stretching; no supine exercises after 1st trimester.
- General: specify sets, reps or duration, and rest periods for every exercise listed.

---

STEP 12 — HEALTH GUIDELINES

Include:
- Food guide table (eat more vs. limit/avoid) — tailored to medical conditions if present
- Daily habits table — specific times and durations, not vague advice
- Hydration: specify ml/day based on client's weight (35 ml per kg bodyweight as base)
- Sleep recommendation: 7–9 hours, include specific bedtime/wake-time suggestion

---

STEP 13 — FINAL VALIDATION

Before producing output:
- Verify each Day Total matches the calorie target within ±3%.
- Verify each macro is within the allowed variance.
- Verify no meal is repeated more than twice across the 7-day plan.
- Do NOT write a verification note or adjustments section — just fix the quantities silently.

---

FOOD REALISM RULES (non-negotiable):
- Fruit: protein <2g and fat <1g per 100g. A fruit row with 15g protein is WRONG.
- Nuts/seeds: fat 45–65g/100g, protein 15–30g/100g, carbs 10–30g/100g. 30g nuts ≈ 6g fat — NEVER 38g carbs.
- Eggs: table shows Whole egg = 156 kcal/100g. So 50g (1 large egg) = 50 × 1.56 = 78 kcal, 6.5g P, 0.6g C, 5.5g F. Use 50g per egg. Never write 78g as the quantity for 1 egg.
- Protein distribution: at least 2 meals per day must provide ≥25g protein.
- Fats from oil/ghee/nuts: list as separate ingredient rows.
- Portion realism: chicken breast serving = 100–180g cooked. Rice serving = 150–250g cooked. Oats = 60–80g dry. Never recommend 500g rice in a single meal.

COOKED vs RAW CONVENTION:
- Grains (rice, oats, quinoa) and dal/legumes → COOKED weights.
- Meats (chicken, fish, mutton) → RAW weights.
- State this once in the Assumptions block.

NEVER write: "As a language model", "As an AI", "Please consult a doctor", "This is not medical advice", or any similar disclaimer. Write only as the nutritionist.

Do not mention apps, websites, technology tools, source documents, file names, PDFs, or knowledge base references in the plan.

If PRIORITY ADJUSTMENTS are listed at the top of the user message, apply every single one — they override all defaults.

---

EVIDENCE-BASED NUTRITION GUIDELINES (WHO + ICMR 2020 — apply to every plan):

DAILY TARGETS BY GOAL:
- Weight loss: 300–500 kcal deficit below TDEE (max 0.5 kg/week loss)
- Muscle gain: 300–500 kcal surplus above TDEE
- Maintenance: match TDEE exactly

MACRONUTRIENT STANDARDS:
- Protein: 0.8g/kg bodyweight (sedentary) → 1.6–2.2g/kg (muscle gain / sports)
- Carbs: 45–65% of total daily energy — prioritise whole grains, pulses, vegetables
- Fat: 20–35% of total energy — saturated fat <10%, zero trans fats
- Fibre: minimum 25g/day from vegetables, legumes, whole grains, fruits

INDIAN DAILY FOOD UNITS (ICMR 2020 balanced plate):
- Cereals/millets: 270–300g/day
- Pulses/legumes: 80g/day
- Dairy: 300ml/day
- Green leafy vegetables: 100g/day
- Other vegetables: 200g/day
- Fruits: 100–150g/day (2 servings)
- Nuts & seeds: 30g/day
- Fats & oils: 20–25g/day

KEY MICRONUTRIENTS (Indian population — commonly deficient):
- Iron: 17–21mg/day women, 9–10mg/day men — always pair iron-rich foods with vitamin C
- Calcium: 600–1000mg/day — dairy, ragi, sesame, leafy greens
- Vitamin D: 600–800 IU/day — include eggs, fatty fish, mushrooms; note sun exposure
- Vitamin B12: critical for vegetarians — include eggs, dairy or fortified foods
- Iodine: use iodized salt only

CONDITION-SPECIFIC RULES (mandatory — apply strictly):
DIABETES: Low-GI foods only (brown rice, millets, oats, whole pulses). Plate: 50% non-starchy veg + 25% whole grain + 25% protein. Avoid white rice, maida, sugar, fruit juice, fried foods.
PCOS/PCOD: Low-GI diet, high protein, anti-inflammatory foods. Avoid refined carbs, sugary drinks, excess starchy vegetables.
HYPERTENSION: DASH diet — high potassium (fruits, vegetables, pulses), low sodium (<5g salt/day), low saturated fat. Avoid processed foods, pickles, cured meats, excess salt.
HYPOTHYROID: Include selenium (eggs, fish, mushrooms), zinc (seeds, legumes), iodized salt. Limit cruciferous vegetables to 2x/week (cook them — reduces goitrogens). Avoid raw soy, raw cabbage/broccoli in large amounts.
HEART CONDITIONS: Low saturated fat, high omega-3 (fish, flaxseeds, walnuts), high fibre. Avoid fried foods, red meat, full-fat dairy, trans fats.
JOINT PAIN / ARTHRITIS: Anti-inflammatory foods — turmeric, ginger, omega-3 rich fish, colourful vegetables. Avoid red meat, processed foods, excess sugar.
PREGNANT / BREASTFEEDING: Extra 300–500 kcal/day, folate (leafy greens, pulses), iron, calcium, DHA (fish, flaxseeds). No alcohol, no high-mercury fish.

PROTEIN DISTRIBUTION: Spread protein across ALL meals — minimum 25g protein in at least 3 meals per day. Never concentrate all protein in one meal.

HYDRATION: 35ml × bodyweight (kg) = daily water target. Always state this in the plan."""


async def _gpt_call(prompt: str, max_tokens: int = 4000) -> str:
    """Single GPT-4o call with timeout and error handling."""
    client = get_client()
    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="openai/gpt-4o",
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.25,
                max_tokens=max_tokens,
            ),
            timeout=300,
        )
        return response.choices[0].message.content or ""
    except asyncio.TimeoutError:
        log.error("GPT-4o call timed out after 300 seconds")
        raise
    except Exception as e:
        log.error(f"GPT-4o call failed: {e}")
        raise


async def generate_diet_plan(
    client_data: dict,
    targets: CalorieTargets,
    progress_cb: Optional[Callable[[int, str], Awaitable[None]]] = None,
    extra_instructions: str = "",
) -> Tuple[str, List[str], List[dict]]:
    """
    Generate a personalized weekly diet & fitness plan (Mon–Sun).
    Single GPT-4o call — fast, clean, calorie-focused.
    extra_instructions: optional nutritionist notes from admin chat session.
    """
    from datetime import date

    async def _progress(pct: int, stage: str):
        if progress_cb:
            try:
                await progress_cb(pct, stage)
            except Exception:
                pass

    name = client_data.get("full_name", "Client")
    log.info(f"Starting plan generation for: {name}")

    await _progress(5, "Searching nutrition knowledge base...")

    # RAG context from local knowledge base
    query = build_client_query(client_data)
    mhb_context, sources, rag_chunks = retrieve_relevant_context(query, k=5)
    await _progress(15, "Knowledge base ready — building your plan...")

    rag_ctx = ""
    if mhb_context:
        rag_ctx = (
            "[NUTRITION REFERENCE — use as primary scientific source]\n"
            f"{mhb_context[:2000]}\n---\n\n"
        )

    # ── Client profile — extract every field ────────────────────────────────────
    goal_key   = client_data.get("goal", "maintain")
    goal_label = GOAL_LABELS.get(goal_key, "Maintain Weight")
    diet_type  = client_data.get("diet_type", "non_vegetarian")
    diet_note  = DIET_TYPE_NOTES.get(diet_type, "")

    conditions  = client_data.get("medical_conditions", []) or []
    allergies   = client_data.get("food_allergies", []) or []
    cuisines    = client_data.get("cuisine_preference", []) or []
    dislikes    = client_data.get("food_dislikes", "") or ""

    city     = client_data.get("city", "") or ""
    state    = client_data.get("state", "") or ""
    location = ", ".join(filter(None, [city, state])) or "India"

    cuisine_str   = ", ".join(cuisines) if cuisines else f"local foods from {location}"
    allergy_str   = ", ".join(allergies) if allergies else "None"
    condition_str = ", ".join(conditions) if conditions else "None"

    # Lifestyle & health fields
    stress_level        = (client_data.get("stress_level") or "").replace("_", " ")
    work_type           = (client_data.get("work_type") or "").replace("_", " ")
    exercise_freq       = client_data.get("exercise_frequency") or ""
    meals_per_day       = int(client_data.get("meals_per_day") or 5)
    meal_timings        = client_data.get("meal_timings") or ""
    digestive_issues    = client_data.get("digestive_issues") or "no"
    digestive_desc      = (client_data.get("digestive_description") or "").strip()
    menstrual_irr       = client_data.get("menstrual_irregularities") or False
    is_pregnant         = client_data.get("is_pregnant") or False
    is_breastfeeding    = client_data.get("is_breastfeeding") or False
    current_meds        = (client_data.get("current_medications") or "").strip()
    current_supps       = (client_data.get("current_supplements") or "").strip()
    alcohol_habit       = (client_data.get("alcohol_habit") or "none").replace("_", " ")
    smoking_habit       = (client_data.get("smoking_habit") or "none").replace("_", " ")
    food_budget         = (client_data.get("food_budget") or "").replace("_", " ")
    timeline            = client_data.get("timeline") or ""
    target_weight_kg    = client_data.get("target_weight_kg")

    cal    = int(targets.calorie_target)
    protein = int(targets.protein_g)
    carbs  = int(targets.carb_g)
    fat    = int(targets.fat_g)
    today  = date.today().strftime("%d %B %Y")

    # Pre-distribute daily targets across meals based on client's meals_per_day preference.
    # This gives GPT exact per-meal calorie/macro targets so totals add up correctly.
    if meals_per_day <= 3:
        # 3 meals: Breakfast 30% | Lunch 38% | Dinner 32%  (≈ 700/900/750 for 2356 kcal target)
        _s = (0.30, 0.38, 0.32)
        _meal_labels = [
            ("Breakfast",     "7:30 AM"),
            ("Lunch",         "1:00 PM"),
            ("Dinner",        "7:30 PM"),
        ]
    elif meals_per_day == 4:
        # 4 meals: Breakfast 25% | Lunch 35% | Evening Snack 15% | Dinner 25%
        _s = (0.25, 0.35, 0.15, 0.25)
        _meal_labels = [
            ("Breakfast",     "7:30 AM"),
            ("Lunch",         "1:00 PM"),
            ("Evening Snack", "4:30 PM"),
            ("Dinner",        "7:30 PM"),
        ]
    else:
        # 5 meals (default): Breakfast 25% | Mid-Morning 10% | Lunch 35% | Evening 10% | Dinner 20%
        _s = (0.25, 0.10, 0.35, 0.10, 0.20)
        _meal_labels = [
            ("Breakfast",     "7:30 AM"),
            ("Mid-Morning",   "10:30 AM"),
            ("Lunch",         "1:00 PM"),
            ("Evening Snack", "4:30 PM"),
            ("Dinner",        "7:30 PM"),
        ]
    _meal_cals  = [round(cal     * s) for s in _s]
    _meal_pros  = [round(protein * s) for s in _s]
    _meal_carbs = [round(carbs   * s) for s in _s]
    _meal_fats  = [round(fat     * s) for s in _s]

    # Per-meal calorie TARGETS with concrete portion anchors.
    # Anchors are computed directly from the calorie target so GPT knows what 'enough food' looks like.
    is_veg  = diet_type in ("vegetarian", "eggetarian", "vegan", "jain")
    is_vegan = diet_type == "vegan"

    def _portion_anchor(meal_cal: int, meal_protein: int) -> str:
        """Return a concrete 'for example' line showing correct gram quantities for this meal."""
        # Grain anchor — ~55% of meal calories from grain (ensures adequate carbs)
        grain_g = round((meal_cal * 0.55) / 1.30)           # rice kcal/g = 1.30
        roti_n  = max(1, round((meal_cal * 0.55) / 104))     # 1 roti = 104 kcal

        # Protein anchor — aim for meal_protein grams
        if is_vegan:
            prot_eg = f"dal {round(meal_protein / 0.07)}g cooked"
        elif diet_type == "eggetarian":
            egg_count = max(1, round(meal_protein / 6.5))
            prot_eg = (
                f"{egg_count} eggs ({egg_count*50}g) OR paneer {round(meal_protein / 0.18)}g"
            )
        elif is_veg:
            if meal_protein >= 20:
                prot_eg = f"paneer {round(meal_protein / 0.18)}g OR dal {round(meal_protein / 0.07)}g cooked"
            else:
                prot_eg = f"dal {round(meal_protein / 0.07)}g cooked OR curd 150ml"
        else:
            prot_eg = f"chicken {round(meal_protein / 0.31)}g raw OR {max(1, round(meal_protein / 6.5))} eggs"

        # Fat anchor — 8–15g oil/ghee depending on meal size
        fat_g = max(5, min(15, round((meal_cal * 0.12) / 9.0)))

        return (
            f"    → grain: rice {grain_g}g cooked OR {roti_n} roti | "
            f"protein: {prot_eg} | "
            f"fat: ghee/oil {fat_g}g"
        )

    _meal_targets_lines = []
    for (label, time), c, p, cb, f in zip(_meal_labels, _meal_cals, _meal_pros, _meal_carbs, _meal_fats):
        line = f"  • {label} (~{time}): aim for ~{c} kcal | ~{p}g protein | ~{cb}g carbs | ~{f}g fat"
        # Only add anchors for main meals (skip if < 15% of daily target — likely a snack)
        if c >= cal * 0.15:
            line += "\n" + _portion_anchor(c, p)
        _meal_targets_lines.append(line)

    _meal_targets = "\n".join(_meal_targets_lines)

    # Select relevant foods for this client (diet type + location + goal filtered)
    # This keeps the prompt lean — ~25–30 foods instead of all 80
    selected_foods  = _select_foods_for_client(client_data)
    nutrition_table = _build_nutrition_table(selected_foods)

    # ── Calorie context ─────────────────────────────────────────────────────────
    tdee = int(targets.tdee)
    bmr  = int(targets.bmr)

    if goal_key == "lose_weight":
        deficit = tdee - cal
        expected = f"~{round(deficit * 30 / 7700, 1)} kg fat loss per month"
        calorie_context = (
            f"**{cal} kcal/day** — a deficit of {deficit} kcal below your TDEE ({tdee} kcal). "
            f"Expected result: {expected}. Every kg of fat = 7,700 kcal, so this deficit is safe and sustainable."
        )
    elif goal_key == "gain_muscle":
        surplus = cal - tdee
        expected = f"~{round(surplus * 30 / 7700, 2)} kg lean gain per month"
        calorie_context = (
            f"**{cal} kcal/day** — a surplus of {surplus} kcal above TDEE ({tdee} kcal). "
            f"Expected result: {expected} with consistent resistance training."
        )
    elif goal_key == "gain_muscle_lose_fat":
        if cal > tdee:
            # Target weight > current weight → lean bulk surplus
            surplus = cal - tdee
            calorie_context = (
                f"**{cal} kcal/day** — a lean bulk surplus of {surplus} kcal above TDEE ({tdee} kcal). "
                f"High protein ({protein}g/day) fuels muscle growth while limiting fat gain. "
                f"Requires consistent resistance training."
            )
        else:
            # Body recomposition → moderate deficit
            deficit = tdee - cal
            expected = f"~{round(deficit * 30 / 7700, 1)} kg fat loss + muscle retention per month"
            calorie_context = (
                f"**{cal} kcal/day** — a moderate deficit of {deficit} kcal with very high protein ({protein}g/day). "
                f"This drives fat loss while high protein preserves and builds muscle simultaneously. "
                f"Expected: {expected}. Requires consistent resistance training."
            )
    elif goal_key == "sports_nutrition":
        surplus = cal - tdee
        calorie_context = (
            f"**{cal} kcal/day** — performance surplus of {surplus} kcal for athletic output and recovery. "
            f"High protein ({protein}g) and carb-timed around training sessions."
        )
    else:
        calorie_context = (
            f"**{cal} kcal/day** — maintenance calories to support your health and wellbeing."
        )
        expected = "Stable weight with improved energy and nutrition quality"

    # ── Protein intake context ───────────────────────────────────────────────────
    protein_level_key = client_data.get("protein_intake_level", "not_sure") or "not_sure"
    protein_note = PROTEIN_INTAKE_NOTES.get(protein_level_key, PROTEIN_INTAKE_NOTES["not_sure"])
    # Substitute {protein} placeholder if present
    protein_note = protein_note.replace("{protein}", str(protein))

    # ── Parse client's own foods from current_diet_description ──────────────────
    current_diet_raw = str(client_data.get("current_diet_description", "") or "").strip()
    if current_diet_raw:
        client_foods_block = (
            f"CLIENT'S OWN FOODS (MUST USE AS PRIMARY CHOICES):\n"
            f"The client described their current diet as: \"{current_diet_raw[:400]}\"\n"
            f"RULE: Build the meal plan around the foods the client already eats and enjoys. "
            f"If they eat avocado + bread for breakfast, put that in the primary 'What to Eat' column — do NOT replace it with something unfamiliar like wheat dosa. "
            f"If they eat rice + dal for lunch, put that as primary. "
            f"Use the Alternative column for variety suggestions or improvements — not to replace familiar foods. "
            f"Only deviate from their stated foods if those foods directly conflict with their medical conditions, allergies, or diet type.\n"
        )
    else:
        client_foods_block = ""

    # ── Exercise block ──────────────────────────────────────────────────────────
    exercise_block = _build_exercise_block(client_data)
    sleep_h      = client_data.get("sleep_hours", 7) or 7
    water_l      = client_data.get("water_intake_liters", 2.5) or 2.5
    water_target = max(2.5, float(water_l) + 0.5)

    # ── Build special condition notes for the prompt ─────────────────────────
    special_notes = []
    if is_pregnant:
        special_notes.append("PREGNANT: increase folate, iron, calcium. Avoid raw fish, high-mercury fish, unpasteurised dairy, excess vitamin A. Calorie target includes ~300 kcal pregnancy surplus.")
    if is_breastfeeding:
        special_notes.append("BREASTFEEDING: needs extra 400–500 kcal/day, high calcium (1000mg+), hydration critical. Avoid caffeine excess.")
    if menstrual_irr:
        special_notes.append("MENSTRUAL IRREGULARITIES / PCOS: prioritise iron-rich foods (spinach, lentils, jaggery), zinc, magnesium. Reduce refined carbs and sugar. Anti-inflammatory foods helpful.")
    if digestive_issues == "yes" and digestive_desc:
        special_notes.append(f"DIGESTIVE ISSUES: {digestive_desc}. Use easy-to-digest, low-fibre options where needed. Avoid raw vegetables in large quantities. Include probiotic foods.")
    elif digestive_issues == "yes":
        special_notes.append("DIGESTIVE ISSUES reported. Keep meals easy to digest. Include probiotic foods (curd, buttermilk). Avoid very high-fibre or raw meals.")
    if current_meds.strip():
        special_notes.append(f"CURRENT MEDICATIONS: {current_meds}. Avoid foods that interact with these medications (e.g. grapefruit with statins, vitamin K with blood thinners).")
    if current_supps.strip():
        special_notes.append(f"CURRENT SUPPLEMENTS: {current_supps}. Do not double-count these nutrients in the meal plan. Note in the plan what supplements they are already taking.")
    if alcohol_habit and alcohol_habit not in ("none", ""):
        special_notes.append(f"ALCOHOL: {alcohol_habit}. Account for empty calories if frequent. Recommend liver-supportive foods (leafy greens, cruciferous vegetables).")
    if smoking_habit and smoking_habit not in ("none", "no", ""):
        special_notes.append(f"SMOKING: {smoking_habit}. Prioritise antioxidant-rich foods — vitamin C (guava, amla, citrus), vitamin E, beta-carotene. Higher oxidative stress requires more antioxidants.")
    if stress_level in ("high", "medium"):
        special_notes.append(f"STRESS LEVEL: {stress_level}. Include magnesium-rich foods (nuts, seeds, dark leafy greens), B-vitamins, and adaptogenic foods. Cortisol management is important for fat loss.")
    if work_type == "physical labor":
        special_notes.append("PHYSICAL LABOR job: calorie needs may be higher on workdays. Pre-shift meal should be carb-rich for sustained energy.")

    # ── Condition-specific clinical guidance ──────────────────────────────────
    cond_lower = [c.lower() for c in conditions]
    for cond in cond_lower:
        if "pcos" in cond or "polycystic" in cond:
            special_notes.append(
                "PCOS: The plan MUST explicitly mention PCOS in the header. "
                "Use low-glycaemic foods (brown rice, oats, dalia, millets, legumes). "
                "Reduce refined carbs (maida, white rice, sugar). Include anti-inflammatory foods: turmeric, berries, flaxseed. "
                "Inositol-rich: buckwheat, legumes. Zinc: pumpkin seeds, sesame. Chromium: broccoli, green beans. "
                "Include a dedicated 'PCOS Management Tips' section in Daily Habits."
            )
        if "hypothyroid" in cond or "thyroid" in cond:
            special_notes.append(
                "HYPOTHYROIDISM: The plan MUST explicitly mention Hypothyroidism in the header. "
                "Include iodine-rich foods (iodised salt, seafood if non-allergic). "
                "Selenium: Brazil nuts (1–2/day), sunflower seeds. Zinc: pumpkin seeds, chickpeas. "
                "Cook cruciferous vegetables (cauliflower, cabbage, broccoli) — raw goitrogenic foods reduce thyroid function. "
                "Avoid soy in excess (if on levothyroxine — gap of 4 hours from medication). "
                "Include a dedicated 'Thyroid Health Tips' section in Daily Habits."
            )
        if "diabetes" in cond or "diabetic" in cond or "type 2" in cond or "type 1" in cond:
            special_notes.append(
                "DIABETES: The plan MUST explicitly mention Diabetes in the header. "
                "Use low-GI foods throughout: brown rice, dalia, oats, whole wheat, legumes. "
                "Strictly avoid: refined sugar, white rice, maida, packaged juices, sweets (mithai), fruit juices. "
                "Distribute carbs evenly across all meals — no large carb-heavy meals. "
                "Include cinnamon, methi seeds, karela (bitter gourd), jamun. "
                "Portion sizes MUST be written precisely. "
                "Include a dedicated 'Diabetes Management Tips' section in Daily Habits."
            )
        if "hypertension" in cond or "blood pressure" in cond or "high bp" in cond:
            special_notes.append(
                "HYPERTENSION: The plan MUST explicitly mention Hypertension in the header. "
                "DASH diet principles: reduce sodium — avoid added salt, pickles, papad, processed foods. "
                "Increase potassium: banana, coconut water, sweet potato, spinach, tomatoes. "
                "Magnesium: leafy greens, pumpkin seeds. Calcium: dairy or fortified alternatives. "
                "Avoid: excessive caffeine, alcohol, fried snacks. "
                "Include a dedicated 'Blood Pressure Management Tips' section in Daily Habits."
            )
        if "cholesterol" in cond or "dyslipidemia" in cond or "lipid" in cond:
            special_notes.append(
                "HIGH CHOLESTEROL / DYSLIPIDEMIA: The plan MUST explicitly mention this in the header. "
                "Include soluble fibre: oats, rajma, chana, methi, isabgol. "
                "Healthy fats: olive oil, flaxseed, walnuts (if no nut allergy), fatty fish. "
                "Strictly avoid: ghee excess, fried foods, full-fat dairy, red meat, trans fats (vanaspati, dalda). "
                "Include omega-3 sources. Include a dedicated 'Heart Health Tips' section."
            )
        if "uric acid" in cond or "gout" in cond:
            special_notes.append(
                "HIGH URIC ACID / GOUT: The plan MUST explicitly mention this in the header. "
                "Avoid high-purine foods: red meat, organ meats (liver, kidney), shellfish, beer, yeast extracts, spinach excess, mushrooms excess. "
                "Include: cherries, low-fat dairy, vitamin C rich foods (amla, guava, lemon water). "
                "High water intake (3+ litres/day). Avoid fructose-rich foods and sugary drinks. "
                "Include a dedicated 'Uric Acid Management Tips' section."
            )
        if "fatty liver" in cond or "nafld" in cond or "liver" in cond:
            special_notes.append(
                "FATTY LIVER / NAFLD: The plan MUST explicitly mention this in the header. "
                "Strictly avoid: alcohol, fried foods, excess sugar, refined carbs, processed foods. "
                "Include: leafy greens, cruciferous vegetables, berries, garlic, turmeric, green tea. "
                "Coffee (2 cups/day plain) is beneficial for liver health. "
                "Calorie deficit is therapeutic — ensure client stays in deficit. "
                "Include a dedicated 'Liver Health Tips' section."
            )
        if "anemia" in cond or "anaemia" in cond or "low hemoglobin" in cond or "low haemoglobin" in cond:
            special_notes.append(
                "ANEMIA (LOW HAEMOGLOBIN): The plan MUST explicitly mention Anemia in the header. "
                "Include haem iron: chicken, fish, lean meat. Non-haem iron: spinach, methi, rajma, chana, tofu, jaggery, dates, ragi. "
                "Always pair iron-rich foods with vitamin C (lemon juice, amla, guava) for absorption. "
                "Avoid tea/coffee immediately after meals — reduces iron absorption by 60%. "
                "Include folate: leafy greens, lentils. B12: dairy, eggs, meat. "
                "Include a dedicated 'Anemia Recovery Tips' section."
            )
        if "kidney" in cond or "renal" in cond or "ckd" in cond:
            special_notes.append(
                "KIDNEY DISEASE / CKD: The plan MUST explicitly mention Kidney condition in the header. "
                "Limit potassium-rich foods if high potassium (avoid banana, potato, tomato in excess). "
                "Limit phosphorus: reduce dairy, processed foods, cola drinks, nuts in excess. "
                "Low sodium: no added salt, no pickles. "
                "Protein needs may be LOWER than standard — consult nephrology guidelines. "
                "Include a dedicated 'Kidney Health Tips' section."
            )
        if "pcod" in cond:
            special_notes.append(
                "PCOD: Same as PCOS — use low-GI foods, reduce refined carbs, include zinc and chromium-rich foods. "
                "Include a dedicated 'PCOD Management Tips' section in Daily Habits."
            )

    special_block = ""
    if special_notes:
        special_block = "SPECIAL CLINICAL NOTES — MUST APPLY TO THIS PLAN:\n" + "\n".join(f"• {n}" for n in special_notes) + "\n"

    # ── Build prompt ────────────────────────────────────────────────────────────
    adj_block = ""
    if extra_instructions.strip():
        adj_block = f"""
⚠️ PRIORITY ADJUSTMENTS — READ BEFORE GENERATING — APPLY ALL OF THESE:
{extra_instructions}

These nutritionist instructions OVERRIDE the defaults below. Every single point above MUST be reflected in the generated plan.
---
"""

    prompt = f"""{rag_ctx}{special_block}
CLIENT PROFILE — USE EVERY DETAIL BELOW:
Name: {name} | Age: {client_data.get('age')} | Gender: {client_data.get('gender','').title()}
Weight: {client_data.get('weight_kg')} kg | Height: {client_data.get('height_cm')} cm
Current weight: {client_data.get('weight_kg')} kg | Target weight: {f"{target_weight_kg} kg" if target_weight_kg else "Not specified"}
Goal: {goal_label} | Timeline: {timeline or "Not specified"}
Location: {location} | Cuisine preference: {cuisine_str}
Diet type: {diet_type.replace('_',' ').title()} — {diet_note}
Allergies: {allergy_str}
Food dislikes: {dislikes or 'None'}
Medical conditions: {condition_str}
Current medications: {current_meds or 'None'}
Current supplements: {current_supps or 'None'}

LIFESTYLE:
Activity level: {client_data.get('activity_level','').replace('_',' ')} | Exercise frequency: {exercise_freq or 'Not specified'}
Work type: {work_type or 'Not specified'} | Stress level: {stress_level or 'Not specified'}
Sleep: {sleep_h} hours/night | Water intake: {water_l} litres/day
Alcohol: {alcohol_habit or 'None'} | Smoking: {smoking_habit or 'None'}

MEAL PREFERENCES:
Meals per day: {meals_per_day} | Preferred meal timings: {meal_timings or 'Standard'}
Cooking situation: {client_data.get('cooking_situation','home cooking') or 'home cooking'}
Food budget: {food_budget or 'Not specified'}
Current diet description: {current_diet_raw[:300] or 'Not described'}
Current protein intake: {protein_note}

{client_foods_block}

DIGESTIVE HEALTH:
Digestive issues: {digestive_issues}{f" — {digestive_desc}" if digestive_desc else ""}
{f"Menstrual irregularities / PCOS: Yes" if menstrual_irr else ""}
{f"Pregnant: Yes" if is_pregnant else ""}
{f"Breastfeeding: Yes" if is_breastfeeding else ""}

CALORIE & MACRO TARGETS:
- BMR (at rest): {bmr} kcal/day
- TDEE (with activity): {tdee} kcal/day
- Daily Target: {calorie_context}
- Protein: {protein}g | Carbohydrates: {carbs}g | Healthy Fats: {fat}g
{adj_block}
EXERCISE PLAN (include this in the plan):
{exercise_block}

---

Generate a complete personalized diet and fitness plan using EXACTLY this structure and format:

---

# NutriVeda — Your Personalized Diet & Fitness Plan
**Prepared for:** {name} | **Date:** {today}

---

## YOUR NUMBERS AT A GLANCE

| | |
|---|---|
| **Daily Calorie Target** | **{cal} kcal** |
| **Goal** | {goal_label} — {calorie_context} |
| **Current Weight** | {client_data.get('weight_kg')} kg |
| **Target Weight** | {f"{target_weight_kg} kg" if target_weight_kg else "—"} |
| **Timeline** | {timeline or "—"} |
| **Protein** | {protein}g per day |
| **Carbohydrates** | {carbs}g per day |
| **Healthy Fats** | {fat}g per day |
| **Meals Per Day** | {meals_per_day} |
| **Diet Type** | {diet_type.replace('_',' ').title()} |
| **Location** | {location} |

---

## YOUR MEAL PLAN

> Portions are WEIGHT-BASED only: grams (g) for solids, ml for liquids. "2 eggs (~100g edible)" is fine; "1 cup" or "1 bowl" is NEVER acceptable.
> Each ingredient gets its OWN row — do NOT combine foods in one cell.

NUTRITION REFERENCE TABLE — values are PER GRAM. Formula: kcal = qty_g × kcal_per_g (same for P, C, F).
Category column shows food type: grain / protein / veg / fat / fruit / dairy / beverage.
Use grain + protein + veg + fat in every main meal.
⚠️ DO NOT reproduce, copy, or print this table in your output. Use it ONLY as a silent reference for your calculations.
{nutrition_table}

---

SECTION A — ASSUMPTIONS (write this first, very briefly, before the meal tables):
State: (1) data source = "USDA FoodData Central + Indian IFCT", (2) grain/dal weights are COOKED, meat weights are RAW unless stated, (3) egg size = large (~50g edible), (4) any Indian dish recipe assumptions (idli, dosa, upma, sambar, chutney).

---

SECTION B — MEAL PLAN (Monday through Sunday)

CRITICAL: You MUST include ALL 7 days — Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, AND Sunday. Do NOT stop before Sunday. If running long, keep each day's description brief but complete. Every day must have a Day Total row.

IMPORTANT: Keep output concise. Do not write explanatory paragraphs between days.

MANDATORY PROCESS — follow for EVERY day:
1. Generate breakfast, lunch, and dinner meals.
2. Calculate kcal for each ingredient using the NUTRITION REFERENCE TABLE above.
3. Sum to get Day Total.
4. Compare Day Total with target: {cal} kcal (acceptable: {round(cal*0.97)}–{round(cal*1.03)} kcal).
5. If below target → increase portions of EXISTING staple foods: rice, chapati, oats, dal, paneer, eggs.
6. Recalculate. Repeat until Day Total is within ±3%.
7. Only after this is satisfied — write the finalized day.

Do NOT add random foods to increase calories. Increase quantities of staples already in the meal.

7-DAY REQUIREMENT — THIS IS MANDATORY:
You MUST generate Monday, Tuesday, Wednesday, Thursday, Friday, Saturday, AND Sunday.
Do NOT stop at Saturday. Sunday is required. If you are running low on space, write Sunday last and keep it concise — but it MUST appear.

QUALITY RULES — apply to every day:
1. Round ALL ingredient quantities to the nearest 5g (e.g. 170g not 169.6g, 150g not 153g).
2. No decimal quantities in the Qty column — whole numbers rounded to 5 only.
3. Protein per day must be ≥ {protein - 10}g. If short, add eggs, paneer, or dal.
4. Fat per day must be ≤ {fat + 10}g. If over, reduce ghee or oil.
5. Each day must have a complete Meal Total after each meal and a Day Total at the end.

MEAL SIZE TARGETS:
  • Breakfast ≈ {round(cal * 0.30)} kcal
  • Lunch     ≈ {round(cal * 0.38)} kcal
  • Dinner    ≈ {round(cal * 0.32)} kcal

EXAMPLE CORRECTION (target {cal} kcal):
  Generated day: Breakfast {round(cal*0.185)} + Lunch {round(cal*0.263)} + Dinner {round(cal*0.354)} = {round(cal*0.802)} kcal
  Deficit = {round(cal - cal*0.802)} kcal
  Fix → increase rice +100g (+130 kcal), paneer +80g (+237 kcal), chapati +40g (+104 kcal)
  New total ≈ {round(cal*0.802 + 130 + 237 + 104)} kcal ✓

PORTION ANCHOR — start here, adjust to hit target:
{_meal_targets}

NUTRITION TABLE RULES:
- Use the NUTRITION REFERENCE TABLE for every food calculation. Do NOT estimate.
- Coconut chutney is NOT pure fat — use the table values exactly.
- Fat target: {fat}g/day (max {fat+10}g). Count fat from ALL ingredients (eggs, paneer, curd, dosa, chutney).
- Protein target: {protein}g/day. Each meal needs ~{round(protein/meals_per_day)}g minimum.

TABLE FORMAT — each ingredient row:
| Meal | Ingredient | Qty (g/ml) | kcal | Protein (g) | Carbs (g) | Fat (g) | Local / Affordable Alternative |

CALCULATION (per-gram values — multiply directly):
  kcal = qty_g × kcal_per_g  |  P = qty_g × P_per_g  |  C = qty_g × C_per_g  |  F = qty_g × F_per_g
  Example: White rice 200g → kcal = 200 × 1.30 = 260, P = 200 × 0.027 = 5.4g

NATURAL PORTIONS — write these naturally, not as raw grams:
  • Eggs: "2 eggs (~100g)" not "egg 100g"
  • Banana: "1 banana (~120g)" not "banana 100g"
  • Roti: "2 roti (~80g)" not "roti 80g"
  • Idli: "3 idli (~150g)" not "idli 150g"

After each meal: add Meal Total row. After all meals: add Day Total row.
Day Total must be {cal} kcal ±3% with macros: protein ±10g, carbs ±25g, fat ±10g.

FOOD SELECTION:
1. Client's own foods (from "Current diet description") are PRIMARY.
2. Adjust quantities to hit calorie targets — do not substitute familiar foods.
3. Vary foods each day for the week.
4. Diet type: {diet_type.replace('_',' ')} — {diet_note}
5. ⚠️ STRICT ALLERGEN RULE — CLIENT HAS DECLARED ALLERGIES: {allergy_str}
   DO NOT include ANY of these or their derivatives anywhere in the plan:
   • dairy allergy → NO milk, paneer, curd, yogurt, ghee, butter, cheese, lassi, buttermilk, whey, cream, khoa
   • gluten allergy → NO wheat, atta, maida, roti, paratha, bread, pasta, semolina/suji, upma, barley
   • nut/tree nut allergy → NO almonds, cashews, walnuts, pistachios, almond milk, peanut butter, nut oils
   • peanut allergy → NO peanuts, groundnuts, peanut butter, groundnut oil — even in cooking
   • egg allergy → NO eggs in any form
   • fish allergy → NO fish, tuna, salmon, mackerel, sardines, anchovies, hilsa, rohu
   • shellfish allergy → NO prawns, shrimp, crab, lobster, squid
   • soy allergy → NO tofu, soya, soy milk, edamame, tempeh
   VIOLATION of allergen rules is a serious safety risk. Double-check every ingredient.
6. Medical conditions (adapt plan accordingly): {condition_str}

EXAMPLE STRUCTURE (Monday — replace with client's actual foods):
### MONDAY
| Meal | Ingredient | Qty (g/ml) | kcal | Protein (g) | Carbs (g) | Fat (g) | Local / Affordable Alternative |
|------|-----------|------------|------|-------------|-----------|---------|-------------------------------|
| Breakfast | Oats (cooked) | 200g | 142 | 5.0 | 24.0 | 3.0 | poha |
| | 2 eggs (~100g) | 100g | 156 | 13.0 | 1.2 | 11.0 | paneer 80g |
| | 1 banana (~120g) | 120g | 107 | 1.3 | 27.6 | 0.4 | apple |
| | Full-fat milk | 200ml | 122 | 6.4 | 9.6 | 6.6 | curd 150g |
| **Meal Total** | | | **527** | **25.7** | **62.4** | **21.0** | |
| **Day Total** | | | **{cal}** | **{protein}** | **{carbs}** | **{fat}** | |

Write all 7 days this way. Calculate every ingredient — do not copy values from previous days.

---

SECTION C — WEEKLY SUMMARY (after all 7 days)
Write a simple table:
| Day | kcal | Protein (g) | Carbs (g) | Fat (g) |
Then add an "Average" row at the bottom.

---

## EXERCISE SCHEDULE

Use the exercise table from the client profile above as the base.
Add a brief header: "Based on your preference and activity level — follow this weekly schedule."
If the client has medical conditions ({condition_str}), adapt exercises as needed — e.g. replace high-impact moves with low-impact alternatives.

| Day | Activity | Duration | Benefit |
|-----|----------|----------|---------|
[Copy or adapt the 7 rows from the exercise table above — modify for medical conditions if needed]

**Pre-workout (30 min before):** A small carb-rich snack — banana, dates, or oats (~150 kcal)
**Post-workout (within 30 min):** A protein source — eggs, curd, chicken, paneer or legumes (~25–30g protein)

---

## FOOD GUIDE

| Eat More | Why | Limit / Avoid | Why |
|----------|-----|---------------|-----|
[Write 6 rows — 6 foods to eat more, 6 foods to limit/avoid, all specific to {goal_label} and {condition_str}]
[Use local food examples from {location}]

---

## DAILY HABITS

| Time | Habit | Benefit |
|------|-------|---------|
| On waking | 300 ml warm water + lemon | Kickstarts metabolism and digestion |
| Before each meal | 200 ml water | Reduces portion size, improves digestion |
| Exercise time | Pre/post workout nutrition as above | Maximises performance and recovery |
| Evening | Avoid heavy meals after 8:00 PM | Better digestion, improved sleep quality |
| Bedtime | By 10:30–11:00 PM | Growth hormone peaks during early sleep |
| **Water target** | **{water_target:.1f} litres per day** | Supports fat metabolism and kidney function |
| **Sleep target** | **{int(sleep_h)}–{int(sleep_h)+1} hours per night** | Essential for fat loss, muscle repair, and energy |

---

## A NOTE FROM YOUR NUTRITIONIST

Write a warm, personal 2–3 sentence message directly to {name} from their nutritionist. Be specific to their goal ({goal_label}), encouraging, and human — not generic or corporate.

---

*This plan is prepared exclusively for {name}. For any adjustments or questions, contact your nutritionist directly.*"""

    # ── Single GPT call ─────────────────────────────────────────────────────────
    await _progress(20, "Crafting your personalized plan...")
    log.info(f"Starting GPT-4o plan generation for {name}...")

    try:
        plan = await _gpt_call(prompt, max_tokens=16384)
        log.info(f"Plan generated — {len(plan)} characters | {len(sources)} knowledge base sources")
    except Exception as e:
        log.error(f"Plan generation failed for {name}: {e}")
        raise RuntimeError(f"Plan generation failed: {e}")

    # ── Two-pass validation: Python adjust first, GPT only if still off ─────
    await _progress(80, "Verifying and correcting calorie totals...")
    try:
        plan = await _verify_and_correct_plan(plan, targets, nutrition_table, food_db=selected_foods)
    except Exception as e:
        log.warning(f"Auto-correction skipped (non-fatal): {e}")

    await _progress(95, "Finalizing your plan...")
    return plan.strip(), sources, rag_chunks
