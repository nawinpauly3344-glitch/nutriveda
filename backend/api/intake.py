"""Client intake form API endpoints."""

import logging
import asyncio
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime

from models.database import get_db, ClientSubmission, DietPlan, PlanStatus
from models.schemas import FullIntakeForm, SubmissionResponse
from diet.calculator import calculate_targets

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/intake", tags=["Intake"])


@router.post("/submit", response_model=SubmissionResponse)
async def submit_intake_form(
    form: FullIntakeForm,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Accept a completed intake form, calculate BMR/TDEE, save to DB,
    and trigger background diet plan generation.
    """
    s1 = form.step1
    s2 = form.step2
    s3 = form.step3
    s4 = form.step4
    s5 = form.step5

    # Calculate BMR, TDEE, macros
    targets = calculate_targets(
        weight_kg=s1.weight_kg,
        height_cm=s1.height_cm,
        age=s1.age,
        gender=s1.gender.value,
        activity_level=s3.activity_level.value,
        goal=s1.goal.value,
        target_weight_kg=s1.target_weight_kg,
        is_breastfeeding=s2.is_breastfeeding,
        is_pregnant=s2.is_pregnant,
    )

    # Build flat client dict for generator
    client_data = {
        "full_name": s1.full_name,
        "age": s1.age,
        "gender": s1.gender.value,
        "height_cm": s1.height_cm,
        "weight_kg": s1.weight_kg,
        "goal": s1.goal.value,
        "target_weight_kg": s1.target_weight_kg,
        "timeline": s1.timeline,
        "email": s1.email,
        "phone": s1.phone,
        "medical_conditions": s2.medical_conditions,
        "current_medications": s2.current_medications,
        "food_allergies": s2.food_allergies,
        "digestive_issues": s2.digestive_issues,
        "digestive_description": s2.digestive_description,
        "menstrual_irregularities": s2.menstrual_irregularities,
        "is_pregnant": s2.is_pregnant,
        "is_breastfeeding": s2.is_breastfeeding,
        "activity_level": s3.activity_level.value,
        "exercise_preference": s3.exercise_preference,
        "exercise_type": s3.exercise_type,
        "exercise_frequency": s3.exercise_frequency,
        "sleep_hours": s3.sleep_hours,
        "stress_level": s3.stress_level,
        "work_type": s3.work_type,
        "meals_per_day": s3.meals_per_day,
        "meal_timings": s3.meal_timings,
        "diet_type": s4.diet_type.value,
        "food_dislikes": s4.food_dislikes,
        "cuisine_preference": s4.cuisine_preference,
        "city": s4.city,
        "state": s4.state,
        "food_budget": s4.food_budget,
        "cooking_situation": s4.cooking_situation,
        "current_diet_description": s5.current_diet_description,
        "water_intake_liters": s5.water_intake_liters,
        "current_supplements": s5.current_supplements,
        "alcohol_habit": s5.alcohol_habit,
        "smoking_habit": s5.smoking_habit,
        "protein_intake_level": s5.protein_intake_level,
    }

    # Save submission to DB
    submission = ClientSubmission(
        full_name=s1.full_name,
        age=s1.age,
        gender=s1.gender.value,
        height_cm=s1.height_cm,
        weight_kg=s1.weight_kg,
        goal=s1.goal.value,
        target_weight_kg=s1.target_weight_kg,
        timeline=s1.timeline,
        email=s1.email,
        phone=s1.phone,
        medical_conditions=s2.medical_conditions,
        current_medications=s2.current_medications,
        food_allergies=s2.food_allergies,
        digestive_issues=s2.digestive_issues,
        digestive_description=s2.digestive_description,
        menstrual_irregularities=s2.menstrual_irregularities,
        is_pregnant=s2.is_pregnant,
        is_breastfeeding=s2.is_breastfeeding,
        activity_level=s3.activity_level.value,
        exercise_preference=s3.exercise_preference,
        exercise_type=s3.exercise_type,
        exercise_frequency=s3.exercise_frequency,
        sleep_hours=s3.sleep_hours,
        stress_level=s3.stress_level,
        work_type=s3.work_type,
        meals_per_day=s3.meals_per_day,
        meal_timings=s3.meal_timings,
        diet_type=s4.diet_type.value,
        food_dislikes=s4.food_dislikes,
        cuisine_preference=s4.cuisine_preference,
        city=s4.city,
        state=s4.state,
        food_budget=s4.food_budget,
        cooking_situation=s4.cooking_situation,
        current_diet_description=s5.current_diet_description,
        water_intake_liters=s5.water_intake_liters,
        current_supplements=s5.current_supplements,
        alcohol_habit=s5.alcohol_habit,
        smoking_habit=s5.smoking_habit,
        protein_intake_level=s5.protein_intake_level,
        bmr=targets.bmr,
        tdee=targets.tdee,
        calorie_target=targets.calorie_target,
        protein_target_g=targets.protein_g,
        carb_target_g=targets.carb_g,
        fat_target_g=targets.fat_g,
    )

    db.add(submission)
    await db.commit()
    await db.refresh(submission)

    # Create a plan record (starts as GENERATING)
    plan = DietPlan(
        submission_id=submission.id,
        status=PlanStatus.GENERATING,
    )
    db.add(plan)
    await db.commit()
    await db.refresh(plan)

    # Trigger background diet plan generation
    background_tasks.add_task(
        _generate_plan_background,
        submission_id=submission.id,
        plan_id=plan.id,
        client_data=client_data,
        targets=targets,
    )

    log.info(f"Submission #{submission.id} saved. BMR={targets.bmr}, TDEE={targets.tdee}")

    return SubmissionResponse(
        id=submission.id,
        full_name=submission.full_name,
        created_at=submission.created_at,
        bmr=targets.bmr,
        tdee=targets.tdee,
        calorie_target=targets.calorie_target,
        message=(
            f"Thank you {s1.full_name}! Your information has been received. "
            f"Your personalized plan (BMR: {targets.bmr} kcal | TDEE: {targets.tdee} kcal | "
            f"Target: {int(targets.calorie_target)} kcal/day) is being prepared and will be "
            f"sent to you after nutritionist review."
        )
    )


async def _generate_plan_background(
    submission_id: int, plan_id: int, client_data: dict, targets
):
    """Background task: generate diet plan and save to DB."""
    from models.database import AsyncSessionLocal, DietPlan, PlanStatus
    from diet.generator import generate_diet_plan

    async def save_progress(pct: int, stage: str):
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
            plan = result.scalar_one_or_none()
            if plan:
                plan.generation_progress = pct
                plan.generation_stage = stage
                await db.commit()

    try:
        log.info(f"Background generation started — plan #{plan_id}, submission #{submission_id}")
        plan_text, sources, rag_chunks = await generate_diet_plan(client_data, targets, progress_cb=save_progress)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
            plan = result.scalar_one_or_none()
            if plan:
                plan.generated_plan = plan_text
                plan.rag_sources = sources
                plan.rag_chunks = rag_chunks
                plan.status = PlanStatus.PENDING  # Ready for admin review
                plan.generation_progress = 100
                plan.generation_stage = "Plan ready for review!"
                plan.updated_at = datetime.utcnow()
                await db.commit()
                log.info(f"Plan #{plan_id} generated successfully ({len(plan_text)} chars)")

    except Exception as e:
        log.error(f"Plan generation FAILED for submission #{submission_id}: {e}", exc_info=True)
        # Mark plan as failed so admin can see and retry
        try:
            from models.database import AsyncSessionLocal, DietPlan, PlanStatus
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
                plan = result.scalar_one_or_none()
                if plan:
                    plan.status = PlanStatus.FAILED
                    plan.admin_notes = f"Auto-generation failed: {str(e)[:500]}"
                    plan.updated_at = datetime.utcnow()
                    await db.commit()
        except Exception as db_err:
            log.error(f"Could not update plan status to FAILED: {db_err}")
