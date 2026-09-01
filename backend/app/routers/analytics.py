"""Analytics endpoints: per-user usage overview."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.analytics import AnalyticsOverview
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
async def get_overview(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    """Return aggregate usage metrics (videos processed, shorts generated,
    average score, average processing time) for the current user."""
    return analytics_service.get_user_overview(db, user.id)
