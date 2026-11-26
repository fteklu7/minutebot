import logging

from app import db
from app.ai import AIError, get_ai
from app.chunking import chunk_text
from app.models import ActionItem, Chunk, Meeting

log = logging.getLogger(__name__)


def process_meeting(meeting_id, filename=None, audio=None):
    """Runs in the background after an upload.

    audio is None when the user uploaded a text transcript (already saved on
    the meeting). Opens its own session since the request's is closed by now.
    """
    session = db.SessionLocal()
    try:
        meeting = session.get(Meeting, meeting_id)
        if meeting is None:
            return
        ai = get_ai()

        if audio is not None:
            meeting.transcript = ai.transcribe(filename, audio)
            session.commit()

        if not meeting.transcript or not meeting.transcript.strip():
            raise AIError("transcript is empty")

        result = ai.extract(meeting.transcript, meeting.meeting_date)

        meeting.summary = result["summary"]
        meeting.decisions = result["decisions"]
        for item in result["action_items"]:
            meeting.action_items.append(
                ActionItem(task=item["task"], owner=item["owner"], due_date=item["due_date"])
            )

        pieces = chunk_text(meeting.transcript)
        vectors = ai.embed(pieces)
        for i, (text, vec) in enumerate(zip(pieces, vectors)):
            meeting.chunks.append(Chunk(position=i, text=text, embedding=vec))

        meeting.status = "done"
        meeting.error = None
        session.commit()
    except Exception as e:
        session.rollback()
        log.exception("processing meeting %s failed", meeting_id)
        meeting = session.get(Meeting, meeting_id)
        if meeting:
            meeting.status = "failed"
            # AIError messages are written for users, anything else isn't
            meeting.error = str(e) if isinstance(e, AIError) else "processing failed, check server logs"
            session.commit()
    finally:
        session.close()
