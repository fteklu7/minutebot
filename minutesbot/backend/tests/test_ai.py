from datetime import date

import pytest

from app.ai import AIError, OfflineProvider, parse_extraction, resolve_due


def test_parse_good_json():
    raw = """{"summary": "Planned the workshop.", "decisions": ["Move to the 14th"],
      "action_items": [{"task": "Book room", "owner": "Jordan", "due_date": "2026-11-14"}]}"""
    out = parse_extraction(raw)
    assert out["summary"] == "Planned the workshop."
    assert out["action_items"] == [{"task": "Book room", "owner": "Jordan", "due_date": date(2026, 11, 14)}]


def test_parse_strips_code_fences():
    out = parse_extraction('```json\n{"summary": "x", "decisions": [], "action_items": []}\n```')
    assert out["summary"] == "x"


def test_parse_drops_bad_items_and_dates():
    raw = """{"summary": "s", "decisions": ["ok", 5, ""],
      "action_items": [{"task": "", "owner": "A"}, "junk",
                       {"task": "Do it", "owner": "", "due_date": "next friday"}]}"""
    out = parse_extraction(raw)
    assert out["decisions"] == ["ok"]
    assert out["action_items"] == [{"task": "Do it", "owner": None, "due_date": None}]


def test_parse_invalid_json():
    with pytest.raises(AIError):
        parse_extraction("sure! here are your minutes")
    with pytest.raises(AIError):
        parse_extraction("[1, 2]")


def test_resolve_due_weekdays():
    tue = date(2026, 11, 10)  # a Tuesday
    assert resolve_due("Friday", tue) == date(2026, 11, 13)
    assert resolve_due("tuesday", tue) == date(2026, 11, 17)  # same weekday = next week
    assert resolve_due("next Friday", tue) == date(2026, 11, 20)
    assert resolve_due("tomorrow", tue) == date(2026, 11, 11)
    assert resolve_due("2026-12-01", tue) == date(2026, 12, 1)
    assert resolve_due("2026-13-01", tue) is None
    assert resolve_due("someday", tue) is None


def test_offline_extract():
    text = "We decided to meet weekly. Jordan will book the room by Friday. Priya is going to email speakers."
    out = OfflineProvider().extract(text, date(2026, 11, 10))
    assert out["decisions"] == ["We decided to meet weekly."]
    assert {"task": "Book the room", "owner": "Jordan", "due_date": date(2026, 11, 13)} in out["action_items"]
    assert any(i["owner"] == "Priya" and i["due_date"] is None for i in out["action_items"])


def test_offline_embeddings_are_normalized_and_stable():
    p = OfflineProvider()
    a, b = p.embed(["room booking", "room booking"])
    assert a == b
    assert abs(sum(x * x for x in a) - 1) < 1e-9
    assert p.embed([]) == []


def test_offline_transcribe_explains_itself():
    with pytest.raises(AIError, match="OPENAI_API_KEY"):
        OfflineProvider().transcribe("a.mp3", b"...")
