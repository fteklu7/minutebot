import os
import tempfile

# set these before the app is imported so it picks up a throwaway db
# and runs in offline mode (no API calls in tests)
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = os.environ.get("TEST_DATABASE_URL", f"sqlite:///{_tmp}/test.db")
os.environ["OPENAI_API_KEY"] = ""
os.environ["ACCESS_KEY"] = ""

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.db import Base, engine
from app.main import app

SAMPLE = """Okay let's get started. We decided to move the resume workshop to the 14th.
Jordan will book the room in Lawson by Friday. Priya is going to email the
speakers by next week. We agreed the budget for food is two hundred dollars.
Sam will design the flyer. Last thing, nobody has the projector cable."""


@pytest.fixture(autouse=True)
def clean_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    settings.access_key = ""
    yield


@pytest.fixture
def client():
    return TestClient(app)


def upload(client, text=SAMPLE, title="GBM week 9", meeting_date="2026-11-10", name="notes.txt"):
    return client.post(
        "/api/meetings",
        data={"title": title, "meeting_date": meeting_date},
        files={"file": (name, text.encode() if isinstance(text, str) else text, "text/plain")},
    )
