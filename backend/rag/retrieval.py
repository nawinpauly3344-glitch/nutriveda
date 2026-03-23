"""
RAG Retrieval — queries the MHB knowledge base for relevant nutrition information.
Uses custom numpy/JSON vector store (Python 3.14 compatible, no ChromaDB).
"""

import logging
from typing import List, Tuple

log = logging.getLogger(__name__)


def retrieve_relevant_context(
    query: str,
    k: int = 6,
    score_threshold: float = 0.25,
) -> Tuple[str, List[str], List[dict]]:
    """
    Query the MHB knowledge base and return relevant context + source list + full chunks.

    Returns:
        (context_text, list_of_source_labels, list_of_chunk_dicts)
        Each chunk dict: {"source": str, "topic": str, "text": str, "score": float}
    """
    try:
        from rag.vectorstore import search

        results = search(query, k=k, score_threshold=score_threshold)

        if not results:
            log.info(f"No relevant MHB content for query: '{query[:80]}'")
            return "", [], []

        context_parts = []
        sources = []
        chunks = []
        seen_sources = set()

        for meta, score in results:
            source = meta.get("source", "MHB Material")
            topic = meta.get("topic", "")
            text = meta.get("text", "")

            if source not in seen_sources:
                seen_sources.add(source)
                sources.append(f"{topic} ({source})")

            context_parts.append(f"[Source: {topic} | Relevance: {score:.2f}]\n{text}")
            chunks.append({
                "source": source,
                "topic": topic,
                "text": text,
                "score": round(float(score), 4),
            })

        context = "\n\n---\n\n".join(context_parts)
        log.info(f"Retrieved {len(results)} chunks from {len(sources)} MHB sources")
        return context, sources, chunks

    except Exception as e:
        log.error(f"RAG retrieval error: {e}")
        return "", [], []


def build_client_query(client_data: dict) -> str:
    """Build a comprehensive search query from client data for RAG retrieval."""
    parts = []

    goal = client_data.get("goal", "")
    goal_map = {
        "lose_weight": "weight loss fat loss calorie deficit cutting",
        "gain_muscle": "muscle building protein requirements strength training hypertrophy",
        "gain_muscle_lose_fat": "body recomposition muscle gain fat loss high protein deficit resistance training",
        "maintain": "maintenance diet healthy eating balance",
        "medical_management": "medical nutrition therapy clinical dietetics",
        "improve_health": "general health wellness micronutrients immune system",
        "sports_nutrition": "sports performance athlete nutrition endurance strength",
    }
    parts.append(goal_map.get(goal, goal))

    conditions = client_data.get("medical_conditions", [])
    if conditions:
        parts.extend([c for c in conditions if c != "None"])

    diet_type = client_data.get("diet_type", "")
    if diet_type:
        parts.append(f"{diet_type} diet meal plan Indian food")

    gender = client_data.get("gender", "")
    if gender == "female":
        if client_data.get("is_pregnant"):
            parts.append("pregnancy nutrition prenatal diet")
        elif client_data.get("is_breastfeeding"):
            parts.append("breastfeeding lactation nutrition")
        elif client_data.get("menstrual_irregularities"):
            parts.append("PCOS hormonal imbalance women nutrition")

    activity = client_data.get("activity_level", "")
    if activity:
        parts.append(f"{activity} activity level calorie requirements energy balance")

    parts.append("Indian diet plan macronutrients meal timing BMR TDEE")

    return " ".join(parts)
