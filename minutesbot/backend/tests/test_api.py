from app.config import settings
from tests.conftest import upload


def test_health(client):
    assert client.get("/api/health").json()["ai"] == "offline"


def test_upload_transcript_end_to_end(client):
    r = upload(client)
    assert r.status_code == 202
    meeting_id = r.json()["id"]

    # TestClient runs background tasks before returning, so it's already done
    m = client.get(f"/api/meetings/{meeting_id}").json()
    assert m["status"] == "done", m["error"]
    assert "We decided to move the resume workshop to the 14th." in m["decisions"]

    items = {i["owner"]: i for i in m["action_items"]}
    assert items["Jordan"]["task"] == "Book the room in Lawson"
    assert items["Jordan"]["due_date"] == "2026-11-13"
    assert items["Priya"]["due_date"] == "2026-11-17"
    assert items["Sam"]["due_date"] is None

    listing = client.get("/api/meetings").json()
    assert listing[0]["open_items"] == 3


def test_search_finds_the_right_meeting(client):
    upload(client, title="Budget meeting", text="We talked about catering. The food budget is two hundred dollars.")
    upload(client, title="Social", text="Bowling night is on Saturday. Everyone brings a friend.")
    results = client.get("/api/search", params={"q": "food budget"}).json()
    assert results[0]["meeting_title"] == "Budget meeting"


def test_search_validation(client):
    assert client.get("/api/search", params={"q": "   "}).status_code == 422
    assert client.get("/api/search", params={"q": "x" * 501}).status_code == 422
    assert client.get("/api/search", params={"q": "anything"}).json() == []


def test_edit_and_complete_items(client):
    mid = upload(client).json()["id"]
    item = next(i for i in client.get(f"/api/meetings/{mid}").json()["action_items"] if i["owner"] == "Sam")
    url = f"/api/action-items/{item['id']}"

    assert client.patch(url, json={"owner": "  Priya  "}).json()["owner"] == "Priya"
    assert client.patch(url, json={"owner": "   "}).json()["owner"] is None  # blank = unassigned
    assert client.patch(url, json={"due_date": "2026-12-01"}).json()["due_date"] == "2026-12-01"
    assert client.patch(url, json={"due_date": None}).json()["due_date"] is None

    assert client.patch(url, json={"task": "   "}).status_code == 422
    assert client.patch(url, json={"task": None}).status_code == 422
    assert client.patch(url, json={"done": None}).status_code == 422
    assert client.patch(url, json={"owner": "x" * 101}).status_code == 422
    assert client.patch("/api/action-items/999", json={"done": True}).status_code == 404

    client.patch(url, json={"done": True})
    open_ids = [i["id"] for i in client.get("/api/action-items").json()]
    assert item["id"] not in open_ids
    all_ids = [i["id"] for i in client.get("/api/action-items", params={"open_only": False}).json()]
    assert item["id"] in all_ids


def test_items_sorted_by_due_date(client):
    upload(client)
    dues = [i["due_date"] for i in client.get("/api/action-items").json()]
    assert dues == ["2026-11-13", "2026-11-17", None]


def test_upload_rejects_bad_files(client):
    assert upload(client, name="notes.exe").status_code == 415
    assert upload(client, text=b"").status_code == 400
    assert upload(client, text=b"\xff\xfe\xfa").status_code == 400
    assert upload(client, title="   ").status_code == 422


def test_upload_size_limit(client):
    old = settings.max_upload_mb
    settings.max_upload_mb = 1
    try:
        assert upload(client, text="a" * (1024 * 1024 + 10)).status_code == 413
    finally:
        settings.max_upload_mb = old


def test_audio_without_key_fails_with_a_useful_message(client):
    mid = upload(client, name="meeting.mp3", text=b"fake audio").json()["id"]
    m = client.get(f"/api/meetings/{mid}").json()
    assert m["status"] == "failed"
    assert "OPENAI_API_KEY" in m["error"]


def test_empty_transcript_fails(client):
    mid = upload(client, text="   \n  ").json()["id"]
    assert client.get(f"/api/meetings/{mid}").json()["status"] == "failed"


def test_delete_meeting(client):
    mid = upload(client).json()["id"]
    assert client.delete(f"/api/meetings/{mid}").status_code == 204
    assert client.get(f"/api/meetings/{mid}").status_code == 404
    assert client.get("/api/action-items").json() == []
    assert client.delete(f"/api/meetings/{mid}").status_code == 404


def test_access_key(client):
    settings.access_key = "my-secret"
    assert client.get("/api/meetings").status_code == 401
    assert client.get("/api/meetings", headers={"X-Access-Key": "wrong"}).status_code == 401
    assert client.get("/api/meetings", headers={"X-Access-Key": "my-secret"}).status_code == 200
    assert client.get("/api/health").status_code == 200  # health stays public
