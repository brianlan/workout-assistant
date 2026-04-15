"""Plan API router — generate, list, get, track, history, stats."""

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import Settings, get_settings
from app.database import get_session
from app.models import Category, Plan, PlanItem, Video
from app.services.ai_planner import (
    AIServiceError,
    build_prompt,
    call_llm,
    parse_response,
)

router = APIRouter(prefix="/api/plans", tags=["plans"])


class PlanGenerateRequest(BaseModel):
    plan_type: str = "weekly"
    focus_areas: list[str] | None = None
    days_per_week: int | None = None
    duration_weeks: int | None = None


class PlanItemRead(BaseModel):
    id: int
    plan_id: int
    video_id: int | None
    day_position: int
    order_position: int
    completed: bool
    completed_at: datetime | None
    video_title: str | None = None
    video_deleted: bool = False

    model_config = {"from_attributes": True}


class PlanRead(BaseModel):
    id: int
    title: str
    plan_type: str
    parameters: str
    created_at: datetime
    items: list[PlanItemRead] = []

    model_config = {"from_attributes": True}


class PlanHistoryItem(BaseModel):
    id: int
    title: str
    plan_type: str
    created_at: datetime
    total_items: int
    completed_items: int
    completion_pct: float

    model_config = {"from_attributes": True}


class PlanStatsResponse(BaseModel):
    completion_rate: float
    total_plans: int
    total_items: int
    completed_items: int
    category_breakdown: dict[str, int]


class CompletionToggle(BaseModel):
    completed: bool


def _get_settings_config(settings: Settings) -> dict[str, str]:
    """Load AI settings from config.json."""
    config_path = settings.config_path
    if config_path.exists():
        with open(config_path) as f:
            return json.load(f)
    return {}


def _enrich_items(
    session: Session, items: list[PlanItem]
) -> list[dict[str, Any]]:
    """Enrich plan items with video title and deletion status."""
    result = []
    for item in items:
        d = {
            "id": item.id,
            "plan_id": item.plan_id,
            "video_id": item.video_id,
            "day_position": item.day_position,
            "order_position": item.order_position,
            "completed": item.completed,
            "completed_at": item.completed_at,
            "video_title": None,
            "video_deleted": False,
        }
        if item.video_id is not None:
            video = session.get(Video, item.video_id)
            if video:
                d["video_title"] = video.title
            else:
                d["video_deleted"] = True
                d["video_title"] = "Video unavailable"
        else:
            d["video_deleted"] = True
            d["video_title"] = "Video unavailable"
        result.append(d)
    return result


@router.post("/generate", response_model=PlanRead, status_code=201)
def generate_plan(
    data: PlanGenerateRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    """Generate a workout plan using AI."""
    # Get all ready videos from library
    videos = session.exec(
        select(Video).where(Video.status == "ready")
    ).all()

    if not videos:
        raise HTTPException(
            status_code=400,
            detail="No videos in library. Add some videos first.",
        )

    # Build parameters dict
    params = {"plan_type": data.plan_type}
    if data.focus_areas:
        params["focus_areas"] = data.focus_areas
    if data.days_per_week:
        params["days_per_week"] = data.days_per_week
    if data.duration_weeks:
        params["duration_weeks"] = data.duration_weeks

    # Build prompt
    messages = build_prompt(videos, params)

    # Get AI settings
    config = _get_settings_config(settings)
    base_url = config.get("base_url", "")
    api_key = config.get("api_key", "")
    model = config.get("model_name", "gpt-4")

    if not base_url or not api_key:
        raise HTTPException(
            status_code=400,
            detail="AI API not configured. Please set the API key in settings.",
        )

    # Call LLM
    try:
        response_text = call_llm(base_url, api_key, model, messages)
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Parse response
    valid_ids = {v.id for v in videos}
    try:
        plan_data, items_data = parse_response(response_text, valid_ids)
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"Failed to parse AI response: {e}")

    # Store parameters as JSON
    plan_params = json.dumps(params)

    # Create Plan
    plan = Plan(
        title=plan_data["title"],
        plan_type=plan_data["plan_type"],
        parameters=plan_params,
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)

    # Create PlanItems
    for item_data in items_data:
        item = PlanItem(
            plan_id=plan.id,
            video_id=item_data["video_id"],
            day_position=item_data["day_position"],
            order_position=item_data["order_position"],
        )
        session.add(item)

    session.commit()
    session.refresh(plan)

    # Return enriched plan
    items = session.exec(
        select(PlanItem).where(PlanItem.plan_id == plan.id)
    ).all()
    enriched = _enrich_items(session, items)

    return {
        "id": plan.id,
        "title": plan.title,
        "plan_type": plan.plan_type,
        "parameters": plan.parameters,
        "created_at": plan.created_at,
        "items": enriched,
    }


@router.get("", response_model=list[PlanRead])
def list_plans(
    session: Session = Depends(get_session),
):
    """List all plans."""
    plans = session.exec(select(Plan).order_by(Plan.created_at.desc())).all()
    result = []
    for plan in plans:
        items = session.exec(
            select(PlanItem).where(PlanItem.plan_id == plan.id)
        ).all()
        enriched = _enrich_items(session, items)
        result.append({
            "id": plan.id,
            "title": plan.title,
            "plan_type": plan.plan_type,
            "parameters": plan.parameters,
            "created_at": plan.created_at,
            "items": enriched,
        })
    return result


@router.get("/history", response_model=list[PlanHistoryItem])
def plan_history(
    session: Session = Depends(get_session),
):
    """Get plan history with completion percentages."""
    plans = session.exec(select(Plan).order_by(Plan.created_at.desc())).all()
    result = []
    for plan in plans:
        items = session.exec(
            select(PlanItem).where(PlanItem.plan_id == plan.id)
        ).all()
        total = len(items)
        completed = sum(1 for i in items if i.completed)
        pct = (completed / total * 100) if total > 0 else 0.0
        result.append({
            "id": plan.id,
            "title": plan.title,
            "plan_type": plan.plan_type,
            "created_at": plan.created_at,
            "total_items": total,
            "completed_items": completed,
            "completion_pct": pct,
        })
    return result


@router.get("/stats", response_model=PlanStatsResponse)
def plan_stats(
    session: Session = Depends(get_session),
):
    """Get plan completion statistics."""
    plans = session.exec(select(Plan)).all()
    total_items = 0
    completed_items = 0
    category_counts: dict[str, int] = {}

    for plan in plans:
        items = session.exec(
            select(PlanItem).where(PlanItem.plan_id == plan.id)
        ).all()
        for item in items:
            total_items += 1
            if item.completed:
                completed_items += 1
            if item.video_id is not None:
                video = session.get(Video, item.video_id)
                if video:
                    cat = session.get(Category, video.category_id)
                    if cat:
                        cat_name = cat.name
                        category_counts[cat_name] = category_counts.get(cat_name, 0) + 1

    completion_rate = (completed_items / total_items * 100) if total_items > 0 else 0.0

    return {
        "completion_rate": completion_rate,
        "total_plans": len(plans),
        "total_items": total_items,
        "completed_items": completed_items,
        "category_breakdown": category_counts,
    }


@router.get("/active", response_model=PlanRead)
def get_active_plan(
    session: Session = Depends(get_session),
):
    """Get the most recent plan (active plan)."""
    plan = session.exec(
        select(Plan).order_by(Plan.created_at.desc())
    ).first()
    if not plan:
        raise HTTPException(status_code=404, detail="No plans found")
    items = session.exec(
        select(PlanItem).where(PlanItem.plan_id == plan.id)
    ).all()
    enriched = _enrich_items(session, items)
    return {
        "id": plan.id,
        "title": plan.title,
        "plan_type": plan.plan_type,
        "parameters": plan.parameters,
        "created_at": plan.created_at,
        "items": enriched,
    }


@router.get("/{plan_id}", response_model=PlanRead)
def get_plan(
    plan_id: int,
    session: Session = Depends(get_session),
):
    """Get a single plan with its items."""
    plan = session.get(Plan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    items = session.exec(
        select(PlanItem).where(PlanItem.plan_id == plan_id)
    ).all()
    enriched = _enrich_items(session, items)

    return {
        "id": plan.id,
        "title": plan.title,
        "plan_type": plan.plan_type,
        "parameters": plan.parameters,
        "created_at": plan.created_at,
        "items": enriched,
    }


@router.patch("/{plan_id}/items/{item_id}", response_model=PlanItemRead)
def toggle_item_completion(
    plan_id: int,
    item_id: int,
    data: CompletionToggle,
    session: Session = Depends(get_session),
):
    """Toggle a plan item's completion status."""
    item = session.get(PlanItem, item_id)
    if not item or item.plan_id != plan_id:
        raise HTTPException(status_code=404, detail="Plan item not found")

    item.completed = data.completed
    item.completed_at = datetime.now() if data.completed else None
    session.add(item)
    session.commit()
    session.refresh(item)

    # Enrich for response
    enriched = _enrich_items(session, [item])
    return enriched[0]


@router.post("/{plan_id}/regenerate", response_model=PlanRead, status_code=201)
def regenerate_plan(
    plan_id: int,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
):
    """Regenerate a plan with the same parameters but a new LLM call."""
    old_plan = session.get(Plan, plan_id)
    if not old_plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Parse old parameters
    try:
        params = json.loads(old_plan.parameters)
    except json.JSONDecodeError:
        params = {"plan_type": old_plan.plan_type}

    # Get videos
    videos = session.exec(
        select(Video).where(Video.status == "ready")
    ).all()

    if not videos:
        raise HTTPException(
            status_code=400,
            detail="No videos in library.",
        )

    # Build prompt and call LLM
    messages = build_prompt(videos, params)

    config = _get_settings_config(settings)
    base_url = config.get("base_url", "")
    api_key = config.get("api_key", "")
    model = config.get("model_name", "gpt-4")

    if not base_url or not api_key:
        raise HTTPException(
            status_code=400,
            detail="AI API not configured.",
        )

    try:
        response_text = call_llm(base_url, api_key, model, messages)
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=str(e))

    valid_ids = {v.id for v in videos}
    try:
        plan_data, items_data = parse_response(response_text, valid_ids)
    except AIServiceError as e:
        raise HTTPException(status_code=502, detail=f"Failed to parse AI response: {e}")

    # Create new plan
    new_plan = Plan(
        title=plan_data["title"],
        plan_type=plan_data["plan_type"],
        parameters=old_plan.parameters,
    )
    session.add(new_plan)
    session.commit()
    session.refresh(new_plan)

    for item_data in items_data:
        item = PlanItem(
            plan_id=new_plan.id,
            video_id=item_data["video_id"],
            day_position=item_data["day_position"],
            order_position=item_data["order_position"],
        )
        session.add(item)

    session.commit()
    session.refresh(new_plan)

    items = session.exec(
        select(PlanItem).where(PlanItem.plan_id == new_plan.id)
    ).all()
    enriched = _enrich_items(session, items)

    return {
        "id": new_plan.id,
        "title": new_plan.title,
        "plan_type": new_plan.plan_type,
        "parameters": new_plan.parameters,
        "created_at": new_plan.created_at,
        "items": enriched,
    }
