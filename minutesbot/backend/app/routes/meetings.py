import os
from datetime import date

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.models import ActionItem, Meeting
from app.pipeline import process_meeting
from app.schemas import MeetingOut, MeetingSummary

router = APIRouter(prefix="/meetings", tags=["meetings"])

AUDIO_EXTS = {".mp3", ".m4a", ".wav", ".webm", ".mp4", ".mpeg", ".mpga", ".ogg"}
TEXT_EXTS = {".txt"}


async def read_limited(upload, max_bytes):
    """Read the upload but stop as soon as it goes over the limit, so someone
    can't make us buffer a 2GB file."""
    data = bytearray()
    while chunk := await upload.read(1024 * 1024):
        data.extend(chunk)
        if len(data) > max_bytes:
            raise HTTPException(413, f"file is over the {settings.max_upload_mb} MB limit")
    return bytes(data)


@router.post("", response_model=MeetingOut, status_code=202)
async def upload_meeting(
    background: BackgroundTasks,
    title: str = Form(..., min_length=1, max_length=200),
    meeting_date: date = Form(default_factory=date.today),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    title = title.strip()
    if not title:
        raise HTTPException(422, "title can't be blank")

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in AUDIO_EXTS | TEXT_EXTS:
        raise HTTPException(415, "upload an audio file (mp3, m4a, wav, webm...) or a .txt transcript")

    data = await read_limited(file, settings.max_upload_mb * 1024 * 1024)
    if not data:
        raise HTTPException(400, "file is empty")

    meeting = Meeting(title=title, meeting_date=meeting_date, decisions=[])
    if ext in TEXT_EXTS:
        try:
            meeting.transcript = data.decode("utf-8")
        except UnicodeDecodeError:
            raise HTTPException(400, "transcript must be UTF-8 text")
    db.add(meeting)
    db.commit()

    # transcription can take a minute, so respond now and let the client poll
    if ext in TEXT_EXTS:
        background.add_task(process_meeting, meeting.id)
    else:
        background.add_task(process_meeting, meeting.id, file.filename, data)
    return meeting


@router.get("", response_model=list[MeetingSummary])
def list_meetings(db: Session = Depends(get_db)):
    open_counts = (
        select(ActionItem.meeting_id, func.count().label("n"))
        .where(ActionItem.done.is_(False))
        .group_by(ActionItem.meeting_id)
        .subquery()
    )
    rows = db.execute(
        select(Meeting, func.coalesce(open_counts.c.n, 0))
        .outerjoin(open_counts, open_counts.c.meeting_id == Meeting.id)
        .order_by(Meeting.meeting_date.desc(), Meeting.id.desc())
    ).all()
    return [
        MeetingSummary(
            id=m.id,
            title=m.title,
            meeting_date=m.meeting_date,
            status=m.status,
            open_items=n,
            created_at=m.created_at,
        )
        for m, n in rows
    ]


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.scalar(
        select(Meeting).options(selectinload(Meeting.action_items)).where(Meeting.id == meeting_id)
    )
    if not meeting:
        raise HTTPException(404, "meeting not found")
    return meeting


@router.delete("/{meeting_id}", status_code=204)
def delete_meeting(meeting_id: int, db: Session = Depends(get_db)):
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404, "meeting not found")
    db.delete(meeting)
    db.commit()
