"""Pydantic schemas for request/response validation."""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime
from enum import Enum


class GoalEnum(str, Enum):
    lose_weight = "lose_weight"
    gain_muscle = "gain_muscle"
    gain_muscle_lose_fat = "gain_muscle_lose_fat"
    maintain = "maintain"
    medical_management = "medical_management"
    improve_health = "improve_health"
    sports_nutrition = "sports_nutrition"


class GenderEnum(str, Enum):
    male = "male"
    female = "female"
    other = "other"


class ActivityLevelEnum(str, Enum):
    sedentary = "sedentary"
    lightly_active = "lightly_active"
    moderately_active = "moderately_active"
    very_active = "very_active"
    athlete = "athlete"


class DietTypeEnum(str, Enum):
    vegetarian = "vegetarian"
    non_vegetarian = "non_vegetarian"
    eggetarian = "eggetarian"
    vegan = "vegan"
    jain = "jain"


class PlanStatusEnum(str, Enum):
    pending = "pending"
    generating = "generating"
    failed = "failed"
    approved = "approved"
    edited = "edited"
    sent = "sent"
    completed = "completed"


# ─── Intake Form ─────────────────────────────────────────────────────────────

class Step1BasicInfo(BaseModel):
    full_name: str = Field(..., min_length=2, max_length=200)
    age: int = Field(..., ge=10, le=100)
    gender: GenderEnum
    height_cm: float = Field(..., ge=50, le=300)
    weight_kg: float = Field(..., ge=20, le=500)
    goal: GoalEnum
    target_weight_kg: Optional[float] = None
    timeline: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class Step2HealthMedical(BaseModel):
    medical_conditions: List[str] = []
    current_medications: Optional[str] = None
    food_allergies: List[str] = []
    digestive_issues: str = "no"
    digestive_description: Optional[str] = None
    menstrual_irregularities: bool = False
    is_pregnant: bool = False
    is_breastfeeding: bool = False


class Step3Lifestyle(BaseModel):
    activity_level: ActivityLevelEnum
    exercise_preference: List[str] = []
    exercise_type: Optional[str] = None
    exercise_frequency: Optional[str] = None
    sleep_hours: Optional[float] = None
    stress_level: Optional[str] = None
    work_type: Optional[str] = None
    meals_per_day: Optional[int] = None
    meal_timings: Optional[str] = None


class Step4DietPreferences(BaseModel):
    diet_type: DietTypeEnum
    food_dislikes: Optional[str] = None
    cuisine_preference: List[str] = []
    city: Optional[str] = None
    state: Optional[str] = None
    food_budget: Optional[str] = None
    cooking_situation: Optional[str] = None


class Step5CurrentDiet(BaseModel):
    current_diet_description: Optional[str] = None
    water_intake_liters: Optional[float] = None
    current_supplements: Optional[str] = None
    alcohol_habit: Optional[str] = None
    smoking_habit: Optional[str] = None
    protein_intake_level: Optional[str] = None


class FullIntakeForm(BaseModel):
    step1: Step1BasicInfo
    step2: Step2HealthMedical
    step3: Step3Lifestyle
    step4: Step4DietPreferences
    step5: Step5CurrentDiet


# ─── Response schemas ─────────────────────────────────────────────────────────

class BMRTDEEResult(BaseModel):
    bmr: float
    tdee: float
    calorie_target: float
    protein_target_g: float
    carb_target_g: float
    fat_target_g: float
    activity_multiplier: float
    goal_adjustment: str


class SubmissionResponse(BaseModel):
    id: int
    full_name: str
    created_at: datetime
    bmr: Optional[float]
    tdee: Optional[float]
    calorie_target: Optional[float]
    status: str = "submitted"
    message: str


class ClientSummary(BaseModel):
    id: int
    full_name: str
    age: Optional[int]
    gender: Optional[str]
    goal: Optional[str]
    email: Optional[str]
    created_at: datetime
    plan_status: Optional[str]
    plan_id: Optional[int]


class DietPlanResponse(BaseModel):
    id: int
    submission_id: int
    status: str
    generated_plan: Optional[str]
    final_plan: Optional[str]
    admin_notes: Optional[str]
    rag_sources: List[str] = []
    generation_progress: int = 0
    generation_stage: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class AdminUpdatePlan(BaseModel):
    final_plan: Optional[str] = None
    admin_notes: Optional[str] = None
    status: Optional[PlanStatusEnum] = None


class AdminLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
