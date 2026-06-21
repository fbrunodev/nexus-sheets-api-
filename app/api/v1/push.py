from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.config import settings
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.services.push import save_subscription, delete_subscription

router = APIRouter(prefix="/push", tags=["Push"])


class SubscriptionPayload(BaseModel):
    endpoint: str
    p256dh: str
    auth: str


@router.post("/subscribe", status_code=201)
def subscribe(
    payload: SubscriptionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    save_subscription(db, current_user.id, payload.endpoint, payload.p256dh, payload.auth)
    return {"ok": True}


@router.post("/unsubscribe")
def unsubscribe(
    payload: SubscriptionPayload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    delete_subscription(db, payload.endpoint)
    return {"ok": True}


@router.get("/vapid-public-key")
def get_vapid_public_key():
    return {"public_key": settings.VAPID_PUBLIC_KEY}
