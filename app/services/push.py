import json
from pywebpush import webpush, WebPushException
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.push_subscription import PushSubscription


def save_subscription(db: Session, owner_id: str, endpoint: str, p256dh: str, auth: str) -> PushSubscription:
    existing = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    if existing:
        existing.owner_id = owner_id
        db.commit()
        return existing
    sub = PushSubscription(owner_id=owner_id, endpoint=endpoint, p256dh=p256dh, auth=auth)
    db.add(sub)
    db.commit()
    return sub


def delete_subscription(db: Session, endpoint: str) -> None:
    sub = db.query(PushSubscription).filter(PushSubscription.endpoint == endpoint).first()
    if sub:
        db.delete(sub)
        db.commit()


def send_push_to_user(db: Session, owner_id: str, title: str, body: str) -> None:
    subs = db.query(PushSubscription).filter(PushSubscription.owner_id == owner_id).all()
    payload = json.dumps({"title": title, "body": body})
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    "endpoint": sub.endpoint,
                    "keys": {"p256dh": sub.p256dh, "auth": sub.auth},
                },
                data=payload,
                vapid_private_key=settings.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": settings.VAPID_CLAIMS_EMAIL},
            )
        except WebPushException as e:
            if e.response and e.response.status_code == 410:
                delete_subscription(db, sub.endpoint)
