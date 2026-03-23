"""SQLAlchemy database models for the nutrition consultation system."""

from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Text, Boolean,
    DateTime, JSON, Enum as SAEnum
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
import enum
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"))

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./nutrition.db")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class PlanStatus(str, enum.Enum):
    PENDING = "pending"       # Awaiting generation / admin review
    GENERATING = "generating" # Currently being generated
    FAILED = "failed"         # Generation failed — can retry
    APPROVED = "approved"     # Admin approved, visible to client
    EDITED = "edited"         # Admin edited and approved
    SENT = "sent"             # Emailed to client
    COMPLETED = "completed"   # Consultation completed


class ClientSubmission(Base):
    __tablename__ = "client_submissions"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Step 1 - Basic Info
    full_name = Column(String(200), nullable=False)
    age = Column(Integer)
    gender = Column(String(20))
    height_cm = Column(Float)
    weight_kg = Column(Float)
    goal = Column(String(100))
    target_weight_kg = Column(Float, nullable=True)
    timeline = Column(String(100), nullable=True)
    email = Column(String(200), nullable=True)
    phone = Column(String(20), nullable=True)

    # Step 2 - Health & Medical
    medical_conditions = Column(JSON, default=lambda: [])   # list of strings
    current_medications = Column(Text, nullable=True)
    food_allergies = Column(JSON, default=lambda: [])
    digestive_issues = Column(String(20), default="no")
    digestive_description = Column(Text, nullable=True)
    menstrual_irregularities = Column(Boolean, default=False)
    is_pregnant = Column(Boolean, default=False)
    is_breastfeeding = Column(Boolean, default=False)

    # Step 3 - Lifestyle
    activity_level = Column(String(50))
    exercise_preference = Column(JSON, default=lambda: [])  # yoga, gym, cardio, hiit, home_workout, dance
    exercise_type = Column(Text, nullable=True)
    exercise_frequency = Column(String(50), nullable=True)
    sleep_hours = Column(Float, nullable=True)
    stress_level = Column(String(20), nullable=True)
    work_type = Column(String(50), nullable=True)
    meals_per_day = Column(Integer, nullable=True)
    meal_timings = Column(Text, nullable=True)

    # Step 4 - Diet Preferences
    diet_type = Column(String(50))
    food_dislikes = Column(Text, nullable=True)
    cuisine_preference = Column(JSON, default=lambda: [])
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    food_budget = Column(String(20), nullable=True)
    cooking_situation = Column(String(50), nullable=True)

    # Step 5 - Current Diet
    current_diet_description = Column(Text, nullable=True)
    water_intake_liters = Column(Float, nullable=True)
    current_supplements = Column(Text, nullable=True)
    alcohol_habit = Column(String(50), nullable=True)
    smoking_habit = Column(String(50), nullable=True)
    protein_intake_level = Column(String(100), nullable=True)

    # Calculated values
    bmr = Column(Float, nullable=True)
    tdee = Column(Float, nullable=True)
    calorie_target = Column(Float, nullable=True)
    protein_target_g = Column(Float, nullable=True)
    carb_target_g = Column(Float, nullable=True)
    fat_target_g = Column(Float, nullable=True)

    # Payment
    payment_id = Column(String(200), nullable=True)
    payment_status = Column(String(20), default="unpaid")


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(200), unique=True, nullable=False)
    value = Column(Text, nullable=True)


class DietPlan(Base):
    __tablename__ = "diet_plans"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    status = Column(SAEnum(PlanStatus), default=PlanStatus.PENDING)

    # AI-generated plan (markdown text)
    generated_plan = Column(Text, nullable=True)
    # Admin-edited version (if admin edits)
    final_plan = Column(Text, nullable=True)
    # Admin notes
    admin_notes = Column(Text, nullable=True)

    # Sources used by RAG (simple labels list)
    rag_sources = Column(JSON, default=lambda: [])
    # Full RAG chunks with source file, topic, text excerpt, and relevance score
    rag_chunks = Column(JSON, default=lambda: [])

    # Generation progress (0-100) and current stage label
    generation_progress = Column(Integer, default=0)
    generation_stage = Column(String(200), nullable=True)

    # PDF file path once generated
    pdf_path = Column(String(500), nullable=True)
    # Word document path once generated
    word_path = Column(String(500), nullable=True)

    # Email tracking
    email_sent_at = Column(DateTime, nullable=True)
    email_sent_to = Column(String(200), nullable=True)

    # Admin chat & regeneration tracking
    regeneration_count = Column(Integer, default=0)
    # Accumulated chat instructions across all regeneration sessions.
    # Format: [{"revision": 1, "instructions": ["...", "..."], "timestamp": "ISO"}]
    admin_chat_history = Column(JSON, default=lambda: [])


async def init_db():
    """Create all tables on startup, and run lightweight migrations."""
    import sqlalchemy as sa
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Migrations — safe to run repeatedly (errors = column already exists)
        for sql in [
            "ALTER TABLE client_submissions ADD COLUMN exercise_preference JSON DEFAULT '[]'",
            "ALTER TABLE diet_plans ADD COLUMN generation_progress INTEGER DEFAULT 0",
            "ALTER TABLE diet_plans ADD COLUMN generation_stage TEXT",
            "ALTER TABLE diet_plans ADD COLUMN word_path TEXT",
            "ALTER TABLE diet_plans ADD COLUMN rag_chunks JSON",
            "ALTER TABLE client_submissions ADD COLUMN protein_intake_level TEXT",
            "ALTER TABLE diet_plans ADD COLUMN regeneration_count INTEGER DEFAULT 0",
            "ALTER TABLE diet_plans ADD COLUMN admin_chat_history JSON DEFAULT '[]'",
            "ALTER TABLE client_submissions ADD COLUMN payment_id TEXT",
            "ALTER TABLE client_submissions ADD COLUMN payment_status TEXT DEFAULT 'unpaid'",
        ]:
            try:
                await conn.execute(sa.text(sql))
            except Exception:
                pass


async def get_db():
    """Dependency to get async DB session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
