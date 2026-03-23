"""Admin dashboard API endpoints."""

import os
import logging
import asyncio
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel

from models.database import get_db, ClientSubmission, DietPlan, PlanStatus
from models.schemas import (
    AdminLogin, TokenResponse, ClientSummary, DietPlanResponse, AdminUpdatePlan
)
from api.auth import (
    create_access_token, verify_token,
    ADMIN_USERNAME, ADMIN_PASSWORD
)


class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str
    plan_id: Optional[int] = None
    history: List[ChatMessage] = []


class PriceConfig(BaseModel):
    active_price_inr: int   # actual charge amount (min 10)
    original_price_inr: int = 0  # shown as strikethrough (0 = no strikethrough)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["Admin"])


# ─── Auth ────────────────────────────────────────────────────────────────────

@router.post("/login", response_model=TokenResponse)
async def admin_login(creds: AdminLogin):
    if creds.username != ADMIN_USERNAME or creds.password != ADMIN_PASSWORD:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    token = create_access_token(creds.username)
    return TokenResponse(access_token=token)


# ─── Clients ─────────────────────────────────────────────────────────────────

@router.get("/clients", response_model=List[ClientSummary])
async def list_clients(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """List all client submissions with their plan status."""
    result = await db.execute(
        select(ClientSubmission).order_by(ClientSubmission.created_at.desc())
    )
    submissions = result.scalars().all()

    clients = []
    for sub in submissions:
        # Get associated plan
        plan_result = await db.execute(
            select(DietPlan).where(DietPlan.submission_id == sub.id).limit(1)
        )
        plan = plan_result.scalar_one_or_none()

        clients.append(ClientSummary(
            id=sub.id,
            full_name=sub.full_name,
            age=sub.age,
            gender=sub.gender,
            goal=sub.goal,
            email=sub.email,
            created_at=sub.created_at,
            plan_status=plan.status.value if plan else None,
            plan_id=plan.id if plan else None,
        ))

    return clients


@router.get("/clients/{submission_id}")
async def get_client_detail(
    submission_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """Get full client profile for a submission."""
    result = await db.execute(
        select(ClientSubmission).where(ClientSubmission.id == submission_id)
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    return {
        "id": sub.id,
        "created_at": sub.created_at,
        "full_name": sub.full_name,
        "age": sub.age,
        "gender": sub.gender,
        "height_cm": sub.height_cm,
        "weight_kg": sub.weight_kg,
        "goal": sub.goal,
        "target_weight_kg": sub.target_weight_kg,
        "timeline": sub.timeline,
        "email": sub.email,
        "phone": sub.phone,
        "medical_conditions": sub.medical_conditions,
        "current_medications": sub.current_medications,
        "food_allergies": sub.food_allergies,
        "digestive_issues": sub.digestive_issues,
        "digestive_description": sub.digestive_description,
        "menstrual_irregularities": sub.menstrual_irregularities,
        "is_pregnant": sub.is_pregnant,
        "is_breastfeeding": sub.is_breastfeeding,
        "activity_level": sub.activity_level,
        "exercise_preference": sub.exercise_preference or [],
        "exercise_type": sub.exercise_type,
        "exercise_frequency": sub.exercise_frequency,
        "sleep_hours": sub.sleep_hours,
        "stress_level": sub.stress_level,
        "work_type": sub.work_type,
        "meals_per_day": sub.meals_per_day,
        "meal_timings": sub.meal_timings,
        "diet_type": sub.diet_type,
        "food_dislikes": sub.food_dislikes,
        "cuisine_preference": sub.cuisine_preference,
        "city": sub.city,
        "state": sub.state,
        "food_budget": sub.food_budget,
        "cooking_situation": sub.cooking_situation,
        "current_diet_description": sub.current_diet_description,
        "water_intake_liters": sub.water_intake_liters,
        "current_supplements": sub.current_supplements,
        "alcohol_habit": sub.alcohol_habit,
        "smoking_habit": sub.smoking_habit,
        "bmr": sub.bmr,
        "tdee": sub.tdee,
        "calorie_target": sub.calorie_target,
        "protein_target_g": sub.protein_target_g,
        "carb_target_g": sub.carb_target_g,
        "fat_target_g": sub.fat_target_g,
    }


# ─── Diet Plans ───────────────────────────────────────────────────────────────

@router.get("/plans/{plan_id}")
async def get_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    return {
        "id": plan.id,
        "submission_id": plan.submission_id,
        "status": plan.status.value,
        "generated_plan": plan.generated_plan,
        "final_plan": plan.final_plan,
        "admin_notes": plan.admin_notes,
        "rag_sources": plan.rag_sources or [],
        "generation_progress": int(plan.generation_progress or 0),
        "generation_stage": str(plan.generation_stage) if plan.generation_stage else "",
        "word_path": str(plan.word_path) if plan.word_path else "",
        "regeneration_count": int(plan.regeneration_count or 0),
        "admin_chat_history": plan.admin_chat_history or [],
        "created_at": plan.created_at.isoformat() if plan.created_at else None,
        "updated_at": plan.updated_at.isoformat() if plan.updated_at else None,
    }


@router.patch("/plans/{plan_id}")
async def update_plan(
    plan_id: int,
    update: AdminUpdatePlan,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """Admin edits or approves a diet plan."""
    result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if update.final_plan is not None:
        plan.final_plan = update.final_plan
        plan.status = PlanStatus.EDITED
    if update.admin_notes is not None:
        plan.admin_notes = update.admin_notes
    if update.status is not None:
        plan.status = PlanStatus(update.status.value)

    plan.updated_at = datetime.now(timezone.utc)
    await db.commit()

    return {"success": True, "plan_id": plan_id, "status": plan.status.value}


@router.post("/plans/{plan_id}/approve")
async def approve_plan(
    plan_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """Approve a plan — triggers PDF generation."""
    result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.status = PlanStatus.APPROVED
    plan.updated_at = datetime.now(timezone.utc)
    await db.commit()

    # Get client info for PDF
    sub_result = await db.execute(
        select(ClientSubmission).where(ClientSubmission.id == plan.submission_id)
    )
    sub = sub_result.scalar_one_or_none()

    # Generate PDF in background
    if sub:
        plan_text = plan.final_plan or plan.generated_plan or ""
        background_tasks.add_task(
            _generate_pdf_background,
            plan_id=plan_id,
            plan_text=plan_text,
            client_name=sub.full_name,
            submission_id=sub.id,
        )

    return {"success": True, "plan_id": plan_id, "status": "approved", "pdf": "generating..."}


@router.post("/plans/{plan_id}/send-email")
async def send_plan_email(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """Send the approved plan PDF to the client via email."""
    from services.email import send_diet_plan_email

    result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if plan.status not in (PlanStatus.APPROVED, PlanStatus.EDITED):
        raise HTTPException(status_code=400, detail="Plan must be approved before sending")

    sub_result = await db.execute(
        select(ClientSubmission).where(ClientSubmission.id == plan.submission_id)
    )
    sub = sub_result.scalar_one_or_none()

    if not sub or not sub.email:
        raise HTTPException(status_code=400, detail="Client email not available")

    pdf_path = plan.pdf_path or ""
    plan_text = plan.final_plan or plan.generated_plan or ""
    try:
        success = send_diet_plan_email(
            to_email=sub.email,
            client_name=sub.full_name,
            pdf_path=pdf_path,
            nutritionist_notes=plan.admin_notes or "",
            plan_text=plan_text,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Email failed: {e}")

    if success:
        plan.status = PlanStatus.SENT
        plan.email_sent_at = datetime.now(timezone.utc)
        plan.email_sent_to = sub.email
        await db.commit()
        return {"success": True, "message": f"Email sent to {sub.email}"}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email")


@router.get("/plans/{plan_id}/pdf-download")
async def download_pdf(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """Download the generated PDF for a plan."""
    from fastapi.responses import FileResponse
    import os

    result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    if not plan.pdf_path or not os.path.exists(plan.pdf_path):
        raise HTTPException(status_code=404, detail="PDF not yet generated. Approve the plan first.")

    sub_result = await db.execute(
        select(ClientSubmission).where(ClientSubmission.id == plan.submission_id)
    )
    sub = sub_result.scalar_one_or_none()
    client_name = sub.full_name.replace(" ", "_") if sub else "client"

    return FileResponse(
        plan.pdf_path,
        media_type="application/pdf",
        filename=f"NutritionPlan_{client_name}.pdf",
    )


@router.get("/plans/{plan_id}/word-download")
async def download_word(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """Download the generated Word document for a plan."""
    from fastapi.responses import FileResponse
    import os

    result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    sub_result = await db.execute(
        select(ClientSubmission).where(ClientSubmission.id == plan.submission_id)
    )
    sub = sub_result.scalar_one_or_none()
    client_name = sub.full_name.replace(" ", "_") if sub else "client"

    # Generate on-demand if word doc doesn't exist yet
    if not plan.word_path or not os.path.exists(plan.word_path):
        plan_text = plan.final_plan or plan.generated_plan
        if not plan_text:
            raise HTTPException(status_code=404, detail="No plan text available to generate Word document.")
        from diet.word_export import generate_word_doc
        word_path = generate_word_doc(
            plan_text,
            sub.full_name if sub else "Client",
            plan.submission_id,
            plan_id,
        )
        if not word_path:
            raise HTTPException(status_code=500, detail="Word document generation failed.")
        plan.word_path = word_path
        await db.commit()

    return FileResponse(
        plan.word_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"NutriVeda_Plan_{client_name}.docx",
    )


@router.get("/plans/{plan_id}/admin-doc-download")
async def download_admin_doc(
    plan_id: int,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """Download admin-only knowledge source report for a plan."""
    from fastapi.responses import FileResponse
    import os

    result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    sub_result = await db.execute(
        select(ClientSubmission).where(ClientSubmission.id == plan.submission_id)
    )
    sub = sub_result.scalar_one_or_none()
    client_name = sub.full_name if sub else "Client"

    from diet.word_export import generate_admin_doc
    generated_at = plan.created_at.strftime("%d %B %Y %H:%M") if plan.created_at else None
    admin_path = generate_admin_doc(
        plan_id=plan_id,
        submission_id=plan.submission_id,
        client_name=client_name,
        rag_sources=plan.rag_sources or [],
        rag_chunks=plan.rag_chunks or [],
        plan_generated_at=generated_at,
    )
    if not admin_path:
        raise HTTPException(status_code=500, detail="Admin report generation failed.")

    safe_name = client_name.replace(" ", "_")
    return FileResponse(
        admin_path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"NutriVeda_AdminReport_{safe_name}_Plan{plan_id}.docx",
    )


class RegenerateRequest(BaseModel):
    extra_instructions: Optional[str] = None
    # Current session's admin chat messages (user messages only, as plain strings)
    chat_messages: Optional[list[str]] = None


def _build_instructions_from_history(history: list, revision: int) -> str:
    """
    Format the full accumulated chat history as a structured block for GPT.
    Each regeneration session is numbered so GPT understands the progression.
    """
    if not history:
        return ""
    lines = [f"REVISION {revision} — apply ALL instructions from every previous session:\n"]
    for entry in history:
        rev  = entry.get("revision", "?")
        ts   = (entry.get("timestamp", "") or "")[:10]
        msgs = entry.get("instructions", []) or []
        if not msgs:
            continue
        label = f"[Session {rev}" + (f" — {ts}" if ts else "") + "]:"
        lines.append(label)
        for m in msgs:
            lines.append(f"  • {m}")
    return "\n".join(lines)


@router.post("/plans/{plan_id}/regenerate")
async def regenerate_plan(
    plan_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
    body: Optional[RegenerateRequest] = Body(default=None),
):
    """Regenerate the AI diet plan for a client, optionally including chat instructions."""
    from diet.calculator import calculate_targets

    result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
    plan = result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    sub_result = await db.execute(
        select(ClientSubmission).where(ClientSubmission.id == plan.submission_id)
    )
    sub = sub_result.scalar_one_or_none()
    if not sub:
        raise HTTPException(status_code=404, detail="Submission not found")

    targets = calculate_targets(
        weight_kg=sub.weight_kg,
        height_cm=sub.height_cm,
        age=sub.age,
        gender=sub.gender,
        activity_level=sub.activity_level,
        goal=sub.goal,
        target_weight_kg=sub.target_weight_kg,
    )

    client_data = {c.key: getattr(sub, c.key) for c in sub.__table__.columns}

    # Increment regeneration count
    new_count = int(plan.regeneration_count or 0) + 1
    plan.regeneration_count = new_count

    # Persist current session's chat messages into the cumulative history
    current_msgs = [m.strip() for m in (body.chat_messages or []) if (m or "").strip()]
    history = list(plan.admin_chat_history or [])
    if current_msgs:
        history.append({
            "revision":     new_count,
            "instructions": current_msgs,
            "timestamp":    datetime.now(timezone.utc).isoformat(),
        })
        plan.admin_chat_history = history

    # Build extra_instructions from the FULL accumulated history
    extra_instructions = _build_instructions_from_history(history, new_count)

    plan.status = PlanStatus.GENERATING
    plan.generated_plan = None
    plan.generation_progress = 0
    plan.generation_stage = (
        f"Applying revision #{new_count} with {len(current_msgs)} new instruction(s)..."
        if current_msgs else f"Regenerating (revision #{new_count})..."
    )
    plan.updated_at = datetime.now(timezone.utc)
    await db.commit()

    background_tasks.add_task(
        _regenerate_plan_background,
        plan_id=plan_id,
        client_data=client_data,
        targets=targets,
        extra_instructions=extra_instructions,
    )

    total_instructions = sum(len(e.get("instructions", [])) for e in history)
    msg = f"Regeneration #{new_count} started"
    if total_instructions:
        msg += f" — applying {total_instructions} total instruction(s) across {len(history)} session(s)"
    return {"success": True, "message": msg, "regeneration_count": new_count}


@router.get("/stats")
async def dashboard_stats(
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """Dashboard statistics."""
    total_clients = await db.scalar(select(func.count(ClientSubmission.id)))
    pending_plans = await db.scalar(
        select(func.count(DietPlan.id)).where(DietPlan.status == PlanStatus.PENDING)
    )
    approved_plans = await db.scalar(
        select(func.count(DietPlan.id)).where(DietPlan.status == PlanStatus.APPROVED)
    )
    sent_plans = await db.scalar(
        select(func.count(DietPlan.id)).where(DietPlan.status == PlanStatus.SENT)
    )

    return {
        "total_clients": total_clients or 0,
        "pending_review": pending_plans or 0,
        "approved": approved_plans or 0,
        "sent_to_client": sent_plans or 0,
    }


# ─── Admin Chat (Nutrition AI Assistant) ─────────────────────────────────────

_CHAT_SYSTEM = """You are an expert nutrition consultant assistant for NutriVeda, helping the nutritionist admin.

You have access to:
- MHB nutrition knowledge base (evidence-based clinical nutrition science)
- The current client's diet plan and profile (if provided)

Your role is to help the nutritionist:
- Discuss and improve client plans — suggest specific edits, swaps, or additions
- Answer nutrition science questions grounded in the MHB knowledge base
- Advise on macros, meal timing, supplements, medical conditions, exercise protocols
- Flag any issues with the plan (allergies, medical conflicts, calorie errors)

Rules:
- Be concise and direct — this is a professional tool, not a chatbot
- When suggesting changes to a plan, quote the specific section to edit
- Ground advice in MHB knowledge base when relevant
- Never say "I'm an AI" or mention OpenAI/GPT
- Respond as if you are a senior clinical nutritionist reviewing the plan"""


@router.post("/chat")
async def admin_chat(
    body: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _: str = Depends(verify_token),
):
    """AI nutrition assistant — knows MHB knowledge base + current client plan."""
    from rag.retrieval import retrieve_relevant_context
    from openai import AsyncOpenAI

    # ── Fetch plan + client context ──────────────────────────────────────────
    plan_context = ""
    client_summary = ""
    if body.plan_id:
        plan_result = await db.execute(select(DietPlan).where(DietPlan.id == body.plan_id))
        plan = plan_result.scalar_one_or_none()
        if plan:
            plan_text = (plan.final_plan or plan.generated_plan or "")[:3000]
            if plan_text:
                plan_context = f"\n\n[CURRENT CLIENT PLAN]\n{plan_text}\n[END PLAN]\n"

            sub_result = await db.execute(
                select(ClientSubmission).where(ClientSubmission.id == plan.submission_id)
            )
            sub = sub_result.scalar_one_or_none()
            if sub:
                meds = ", ".join(sub.medical_conditions or []) or "None"
                allergies = ", ".join(sub.food_allergies or []) or "None"
                exercises = ", ".join(sub.exercise_preference or []) or "None"
                client_summary = (
                    f"\n[CLIENT PROFILE]\n"
                    f"Name: {sub.full_name} | Age: {sub.age} | Gender: {sub.gender}\n"
                    f"Weight: {sub.weight_kg}kg | Height: {sub.height_cm}cm\n"
                    f"Goal: {sub.goal} | Diet type: {sub.diet_type}\n"
                    f"Activity: {sub.activity_level} | Exercise: {exercises}\n"
                    f"Calorie target: {int(sub.calorie_target or 0)} kcal | "
                    f"Protein target: {int(sub.protein_target_g or 0)}g\n"
                    f"Medical: {meds} | Allergies: {allergies}\n"
                    f"Location: {sub.city or ''}, {sub.state or ''}\n"
                    f"Protein intake level: {sub.protein_intake_level or 'unknown'}\n"
                    f"[END PROFILE]\n"
                )

    # ── RAG knowledge base retrieval ─────────────────────────────────────────
    try:
        mhb_ctx, sources, _ = retrieve_relevant_context(body.message, k=4)
        rag_block = f"\n[MHB KNOWLEDGE BASE]\n{mhb_ctx[:1500]}\n[END KNOWLEDGE]\n" if mhb_ctx else ""
    except Exception:
        rag_block = ""
        sources = []

    # ── Build messages ───────────────────────────────────────────────────────
    messages = [{"role": "system", "content": _CHAT_SYSTEM}]

    # Inject context as first user turn so it stays in view
    if rag_block or client_summary or plan_context:
        context_block = rag_block + client_summary + plan_context
        messages.append({
            "role": "user",
            "content": f"[CONTEXT FOR THIS SESSION]{context_block}\n\nUse this context to answer my questions below."
        })
        messages.append({
            "role": "assistant",
            "content": "Understood. I have the client profile, their plan, and MHB knowledge ready. What would you like to discuss?"
        })

    # Add conversation history (last 12 messages)
    for msg in body.history[-12:]:
        messages.append({"role": msg.role, "content": msg.content})

    # Add the new message
    messages.append({"role": "user", "content": body.message})

    # ── GPT-4o call ──────────────────────────────────────────────────────────
    try:
        ai = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        response = await asyncio.wait_for(
            ai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=800,
                temperature=0.25,
            ),
            timeout=60,
        )
        reply = response.choices[0].message.content or ""
    except Exception as e:
        log.error(f"Chat GPT call failed: {e}")
        raise HTTPException(status_code=500, detail="AI assistant temporarily unavailable")

    return {"reply": reply, "sources": sources[:4]}


# ─── Background tasks ─────────────────────────────────────────────────────────

async def _generate_pdf_background(
    plan_id: int, plan_text: str, client_name: str, submission_id: int
):
    from models.database import AsyncSessionLocal, DietPlan
    from diet.pdf_export import generate_pdf
    from diet.word_export import generate_word_doc

    try:
        pdf_path = generate_pdf(plan_text, client_name, submission_id, plan_id)
        word_path = generate_word_doc(plan_text, client_name, submission_id, plan_id)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
            plan = result.scalar_one_or_none()
            if plan:
                if pdf_path:
                    plan.pdf_path = pdf_path
                if word_path:
                    plan.word_path = word_path
                plan.updated_at = datetime.now(timezone.utc)
                await db.commit()
                log.info(f"PDF + Word saved for plan #{plan_id}")
    except Exception as e:
        log.error(f"Document generation failed for plan #{plan_id}: {e}")


async def _regenerate_plan_background(plan_id: int, client_data: dict, targets, extra_instructions: str = ""):
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
        log.info(f"Regenerating plan #{plan_id}... extra_instructions={'yes' if extra_instructions else 'no'}")
        plan_text, sources, rag_chunks = await generate_diet_plan(
            client_data, targets, progress_cb=save_progress, extra_instructions=extra_instructions
        )
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
            plan = result.scalar_one_or_none()
            if plan:
                plan.generated_plan = plan_text
                plan.rag_sources = sources
                plan.rag_chunks = rag_chunks
                plan.status = PlanStatus.PENDING
                plan.admin_notes = None  # Clear old error notes
                plan.generation_progress = 100
                plan.generation_stage = "Plan ready for review!"
                plan.updated_at = datetime.now(timezone.utc)
                await db.commit()
                log.info(f"Plan #{plan_id} regenerated successfully")
    except Exception as e:
        log.error(f"Regeneration FAILED for plan #{plan_id}: {e}", exc_info=True)
        try:
            async with AsyncSessionLocal() as db:
                result = await db.execute(select(DietPlan).where(DietPlan.id == plan_id))
                plan = result.scalar_one_or_none()
                if plan:
                    plan.status = PlanStatus.FAILED
                    plan.admin_notes = f"Regeneration failed: {str(e)[:500]}"
                    plan.updated_at = datetime.now(timezone.utc)
                    await db.commit()
        except Exception as db_err:
            log.error(f"Could not mark plan as FAILED: {db_err}")


# ─── Price Config ─────────────────────────────────────────────────────────────

@router.get("/price-config")
async def get_price_config(db: AsyncSession = Depends(get_db), _: str = Depends(verify_token)):
    """Get current active price configuration."""
    from models.database import AppSettings
    result = await db.execute(select(AppSettings).where(AppSettings.key == "active_price_inr"))
    setting = result.scalar_one_or_none()
    price_inr = int(setting.value) if setting else 1999
    # Get custom max price (original price shown as strikethrough)
    max_result = await db.execute(select(AppSettings).where(AppSettings.key == "original_price_inr"))
    max_setting = max_result.scalar_one_or_none()
    original_price = int(max_setting.value) if max_setting else 0
    discount_pct = round((original_price - price_inr) / original_price * 100) if original_price > price_inr > 0 else 0
    return {
        "active_price_inr": price_inr,
        "original_price_inr": original_price,
        "discount_pct": discount_pct,
    }


@router.put("/price-config")
async def update_price_config(config: PriceConfig, db: AsyncSession = Depends(get_db), _: str = Depends(verify_token)):
    """Update active price. Any amount from 10 to 99999."""
    if config.active_price_inr < 10 or config.active_price_inr > 99999:
        raise HTTPException(status_code=400, detail="Price must be between 10 and 99999")
    from models.database import AppSettings
    result = await db.execute(select(AppSettings).where(AppSettings.key == "active_price_inr"))
    setting = result.scalar_one_or_none()
    if setting:
        setting.value = str(config.active_price_inr)
    else:
        db.add(AppSettings(key="active_price_inr", value=str(config.active_price_inr)))
    # Save original price (strikethrough)
    orig_result = await db.execute(select(AppSettings).where(AppSettings.key == "original_price_inr"))
    orig_setting = orig_result.scalar_one_or_none()
    if orig_setting:
        orig_setting.value = str(config.original_price_inr)
    else:
        db.add(AppSettings(key="original_price_inr", value=str(config.original_price_inr)))
    await db.commit()
    return {"success": True, "active_price_inr": config.active_price_inr, "original_price_inr": config.original_price_inr}
