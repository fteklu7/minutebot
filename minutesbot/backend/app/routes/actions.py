from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import ActionItem
from app.schemas import ActionItemOut, ActionItemPatch

router = APIRouter(prefix="/action-items", tags=["action items"])


@router.get("", response_model=list[ActionItemOut])
def list_items(open_only: bool = True, db: Session = Depends(get_db)):
    stmt = select(ActionItem)
    if open_only:
        stmt = stmt.where(ActionItem.done.is_(False))
    # items with no due date go last
    stmt = stmt.order_by(ActionItem.due_date.is_(None), ActionItem.due_date, ActionItem.id)
    return db.scalars(stmt).all()


@router.patch("/{item_id}", response_model=ActionItemOut)
def update_item(item_id: int, body: ActionItemPatch, db: Session = Depends(get_db)):
    item = db.get(ActionItem, item_id)
    if not item:
        raise HTTPException(404, "action item not found")

    changes = body.model_dump(exclude_unset=True)

    if "task" in changes:
        task = (changes["task"] or "").strip()
        if not task:
            raise HTTPException(422, "task can't be blank")
        changes["task"] = task
    if "owner" in changes:
        # blank owner means unassigned
        changes["owner"] = (changes["owner"] or "").strip() or None
    if "done" in changes and changes["done"] is None:
        raise HTTPException(422, "done must be true or false")

    for key, value in changes.items():
        setattr(item, key, value)
    db.commit()
    return item
