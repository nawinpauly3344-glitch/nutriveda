"""
BMR & TDEE Calculator using Mifflin-St Jeor Equation (most accurate).
Calorie and macro target computation.
"""

from dataclasses import dataclass
from typing import Optional


# Activity multipliers
ACTIVITY_MULTIPLIERS = {
    "sedentary": 1.2,
    "lightly_active": 1.375,
    "moderately_active": 1.55,
    "very_active": 1.725,
    "athlete": 1.9,
}

ACTIVITY_LABELS = {
    "sedentary": "Sedentary (desk job, no exercise)",
    "lightly_active": "Lightly Active (1-3 days/week exercise)",
    "moderately_active": "Moderately Active (3-5 days/week exercise)",
    "very_active": "Very Active (6-7 days/week hard exercise)",
    "athlete": "Athlete / Physical Labor",
}


@dataclass
class CalorieTargets:
    bmr: float
    tdee: float
    calorie_target: float
    protein_g: float
    carb_g: float
    fat_g: float
    activity_multiplier: float
    goal_adjustment: str
    bmr_formula: str = "Mifflin-St Jeor"


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: str) -> float:
    """
    Mifflin-St Jeor Equation:
    Men:   BMR = (10 × weight_kg) + (6.25 × height_cm) − (5 × age) + 5
    Women: BMR = (10 × weight_kg) + (6.25 × height_cm) − (5 × age) − 161
    """
    base = (10 * weight_kg) + (6.25 * height_cm) - (5 * age)
    if gender.lower() in ("male", "m"):
        return round(base + 5, 1)
    else:
        return round(base - 161, 1)


def calculate_targets(
    weight_kg: float,
    height_cm: float,
    age: int,
    gender: str,
    activity_level: str,
    goal: str,
    target_weight_kg: Optional[float] = None,
) -> CalorieTargets:
    """Calculate all calorie and macro targets for a client."""

    bmr = calculate_bmr(weight_kg, height_cm, age, gender)
    multiplier = ACTIVITY_MULTIPLIERS.get(activity_level, 1.375)
    tdee = round(bmr * multiplier, 1)

    # Calorie target based on goal
    if goal in ("lose_weight",):
        # Safe deficit = 50% of the gap between TDEE and BMR
        # Example: BMR=1500, TDEE=2500 → gap=1000 → deficit=500 → target=2000
        gap = tdee - bmr
        deficit = round(gap * 0.5, 0)
        calorie_target = round(tdee - deficit, 0)
        calorie_target = max(calorie_target, bmr)  # Absolute floor = BMR
        actual_deficit = round(tdee - calorie_target)
        goal_adj = (
            f"Safe deficit of {actual_deficit} kcal/day "
            f"(50% of TDEE-BMR gap). "
            f"Expected fat loss: ~{round(actual_deficit * 30 / 7700, 1)} kg/month."
        )
    elif goal in ("gain_muscle",):
        calorie_target = round(tdee + 300, 0)
        goal_adj = f"Lean bulk surplus of {round(calorie_target - tdee)} kcal/day for muscle gain"
    elif goal in ("gain_muscle_lose_fat",):
        # Smart direction: target weight > current weight → BULK (surplus)
        #                  target weight <= current weight or none → RECOMP (deficit)
        if target_weight_kg and target_weight_kg > weight_kg:
            # Client wants to gain overall mass → lean bulk surplus
            calorie_target = round(tdee + 300, 0)
            surplus = round(calorie_target - tdee)
            mass_to_gain = round(target_weight_kg - weight_kg, 1)
            goal_adj = (
                f"Lean bulk surplus of {surplus} kcal/day (TDEE + {surplus}). "
                f"Goal: gain {mass_to_gain} kg (current {weight_kg} kg → target {target_weight_kg} kg). "
                f"High protein fuels muscle growth while limiting fat accumulation. "
                f"Requires consistent resistance training."
            )
        else:
            # Body recomposition — shed fat while building/preserving muscle
            raw_deficit = 300
            calorie_target = round(tdee - raw_deficit, 0)
            # Hard floor: never below BMR + 200 kcal (hormonal & recovery minimum)
            calorie_target = max(calorie_target, bmr + 200)
            actual_deficit = round(tdee - calorie_target)
            fat_loss_per_month = round(actual_deficit * 30 / 7700, 1)
            goal_adj = (
                f"Moderate deficit of {actual_deficit} kcal/day (TDEE − {actual_deficit}). "
                f"Expected fat loss: ~{fat_loss_per_month} kg/month with very high protein to "
                f"build/preserve muscle simultaneously. Requires disciplined resistance training."
            )
    elif goal in ("sports_nutrition",):
        calorie_target = round(tdee + 200, 0)
        goal_adj = f"Performance surplus of {round(calorie_target - tdee)} kcal/day"
    elif goal in ("medical_management",):
        calorie_target = tdee
        goal_adj = "Maintenance calories (adjusted per medical condition)"
    else:
        calorie_target = tdee
        goal_adj = "Maintenance calories"

    # Macro split — protein starts at 1g/kg (body weight), scales with activity and goal
    # Base: sedentary = 1.0g/kg, scales up with activity level
    _protein_activity_base = {
        "sedentary": 1.0,
        "lightly_active": 1.1,
        "moderately_active": 1.2,
        "very_active": 1.4,
        "athlete": 1.5,
    }
    # Goal bonus — how much extra protein the goal demands
    _protein_goal_bonus = {
        "lose_weight": 0.1,          # slightly higher to preserve muscle during deficit
        "gain_muscle": 0.3,          # extra for muscle protein synthesis
        "gain_muscle_lose_fat": 0.3, # high protein drives fat loss + muscle retention simultaneously
        "sports_nutrition": 0.3,     # athletic recovery and performance
    }
    base_g_per_kg = _protein_activity_base.get(activity_level, 1.0)
    bonus_g_per_kg = _protein_goal_bonus.get(goal, 0.0)
    protein_per_kg = round(base_g_per_kg + bonus_g_per_kg, 1)

    protein_g = round(weight_kg * protein_per_kg, 0)
    protein_cals = protein_g * 4

    # Fat: 25-30% of total calories
    fat_pct = 0.27
    fat_cals = calorie_target * fat_pct
    fat_g = round(fat_cals / 9, 0)

    # Carbs: remainder
    carb_cals = calorie_target - protein_cals - fat_cals
    carb_g = max(round(carb_cals / 4, 0), 50)  # Never below 50g carbs

    return CalorieTargets(
        bmr=bmr,
        tdee=tdee,
        calorie_target=calorie_target,
        protein_g=protein_g,
        carb_g=carb_g,
        fat_g=fat_g,
        activity_multiplier=multiplier,
        goal_adjustment=goal_adj,
    )
