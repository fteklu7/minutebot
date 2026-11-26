import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.ai import get_ai
from app.models import Chunk


def search_chunks(session, query, limit=5):
    """Cosine similarity over every stored chunk.

    Brute force is fine at org scale (a semester of weekly meetings is a few
    hundred chunks). Past ~100k chunks I'd move this into pgvector.
    """
    q = get_ai().embed([query])[0]
    q = np.array(q, dtype=np.float32)

    chunks = session.scalars(select(Chunk).options(joinedload(Chunk.meeting))).all()
    # skip vectors made by a different embedding model (different length)
    chunks = [c for c in chunks if len(c.embedding) == len(q)]
    if not chunks:
        return []

    matrix = np.array([c.embedding for c in chunks], dtype=np.float32)
    norms = np.linalg.norm(matrix, axis=1) * (np.linalg.norm(q) or 1.0)
    norms[norms == 0] = 1.0
    scores = matrix @ q / norms

    top = np.argsort(-scores)[:limit]
    results = []
    for i in top:
        if scores[i] <= 0:
            break
        c = chunks[i]
        results.append(
            {
                "meeting_id": c.meeting_id,
                "meeting_title": c.meeting.title,
                "meeting_date": c.meeting.meeting_date,
                "text": c.text,
                "score": round(float(scores[i]), 3),
            }
        )
    return results
