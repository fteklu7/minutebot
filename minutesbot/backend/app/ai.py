"""Everything that talks to a model lives here.

There are two providers:
  - OpenAIProvider: the real one (whisper + gpt + embeddings)
  - OfflineProvider: no API key needed. Uses simple rules so the app still
    works for local dev, tests, and demos without spending money.
"""
import hashlib
import json
import math
import re
from datetime import date, timedelta

from app.chunking import split_sentences
from app.config import settings

MAX_TRANSCRIPT_CHARS = 120_000

EXTRACT_PROMPT = """You turn student org meeting transcripts into minutes.
The meeting happened on {meeting_date} ({weekday}).

Return JSON with exactly these keys:
  "summary": 2-4 sentences, plain language
  "decisions": list of strings, things the group agreed on
  "action_items": list of objects with
      "task": what needs to be done, starting with a verb
      "owner": the person responsible as said in the meeting, or null
      "due_date": YYYY-MM-DD or null. Convert relative dates ("by Friday",
                  "next week") using the meeting date. Do not invent dates.

Only include action items someone actually committed to. If there are none,
return an empty list."""


class AIError(Exception):
    pass


def parse_extraction(raw):
    """Parse the model's JSON. Models sometimes wrap it in ``` or return junk,
    so be strict about what we keep."""
    text = raw.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise AIError(f"model returned invalid JSON: {e}") from e
    if not isinstance(data, dict):
        raise AIError("model returned JSON that isn't an object")

    summary = data.get("summary") or ""
    if not isinstance(summary, str):
        summary = str(summary)

    decisions = [d.strip() for d in data.get("decisions") or [] if isinstance(d, str) and d.strip()]

    items = []
    for item in data.get("action_items") or []:
        if not isinstance(item, dict):
            continue
        task = item.get("task")
        if not isinstance(task, str) or not task.strip():
            continue
        owner = item.get("owner")
        owner = owner.strip() if isinstance(owner, str) and owner.strip() else None
        due = None
        if isinstance(item.get("due_date"), str):
            try:
                due = date.fromisoformat(item["due_date"])
            except ValueError:
                due = None  # bad date from the model, just drop it
        items.append({"task": task.strip(), "owner": owner, "due_date": due})

    return {"summary": summary.strip(), "decisions": decisions, "action_items": items}


class OpenAIProvider:
    def __init__(self, api_key):
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, timeout=120)

    def transcribe(self, filename, data):
        result = self.client.audio.transcriptions.create(
            model=settings.transcribe_model, file=(filename, data)
        )
        return result.text

    def extract(self, transcript, meeting_date):
        prompt = EXTRACT_PROMPT.format(
            meeting_date=meeting_date.isoformat(),
            weekday=meeting_date.strftime("%A"),
        )
        resp = self.client.chat.completions.create(
            model=settings.chat_model,
            response_format={"type": "json_object"},
            temperature=0,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": transcript[:MAX_TRANSCRIPT_CHARS]},
            ],
        )
        return parse_extraction(resp.choices[0].message.content or "")

    def embed(self, texts):
        if not texts:
            return []
        out = []
        # batch so a long meeting doesn't become one giant request
        for i in range(0, len(texts), 100):
            resp = self.client.embeddings.create(model=settings.embed_model, input=texts[i : i + 100])
            out.extend(d.embedding for d in resp.data)
        return out


# ---------- offline mode ----------

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
STOPWORDS = set(
    "a an the and or but to of in on for at by with is are was were be it this that "
    "we i you he she they will can should would just so do did our your".split()
)
ACTION_RE = re.compile(r"\b([A-Z][a-z]+)\s+(?:will|is going to|'ll|can)\s+(.+)")
DUE_RE = re.compile(
    r"\s*\b(?:by|before|on)\s+(tomorrow|next week|\d{4}-\d{2}-\d{2}|(?:next\s+)?(?:%s))\b"
    % "|".join(WEEKDAYS),
    re.IGNORECASE,
)


def resolve_due(phrase, meeting_date):
    p = phrase.lower().strip()
    if p == "tomorrow":
        return meeting_date + timedelta(days=1)
    if p == "next week":
        return meeting_date + timedelta(days=7)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", p):
        try:
            return date.fromisoformat(p)
        except ValueError:
            return None
    skip_week = p.startswith("next ")
    day = p.replace("next ", "")
    if day in WEEKDAYS:
        ahead = (WEEKDAYS.index(day) - meeting_date.weekday()) % 7 or 7
        if skip_week:
            ahead += 7
        return meeting_date + timedelta(days=ahead)
    return None


class OfflineProvider:
    def transcribe(self, filename, data):
        raise AIError("audio uploads need OPENAI_API_KEY set. Upload a .txt transcript instead.")

    def extract(self, transcript, meeting_date):
        sentences = split_sentences(transcript)
        decisions = [s for s in sentences if re.search(r"\b(decided|agreed)\b", s, re.I)]

        items = []
        for s in sentences:
            m = ACTION_RE.search(s)
            if not m:
                continue
            owner, task = m.group(1), m.group(2).rstrip(".!? ")
            due = None
            d = DUE_RE.search(task)
            if d:
                due = resolve_due(d.group(1), meeting_date)
                task = (task[: d.start()] + task[d.end() :]).strip(" ,")
            if task:
                items.append({"task": task[0].upper() + task[1:], "owner": owner, "due_date": due})

        summary = " ".join(sentences[:2])
        return {"summary": summary, "decisions": decisions, "action_items": items}

    def embed(self, texts, dims=256):
        # hashing trick: each word goes to a bucket. Not semantic, but good
        # enough for keyword-ish search without an API.
        vectors = []
        for t in texts:
            v = [0.0] * dims
            for w in re.findall(r"[a-z0-9]+", t.lower()):
                if w in STOPWORDS:
                    continue
                h = int(hashlib.md5(w.encode()).hexdigest(), 16)
                v[h % dims] += 1.0
            norm = math.sqrt(sum(x * x for x in v)) or 1.0
            vectors.append([x / norm for x in v])
        return vectors


def get_ai():
    if settings.openai_api_key:
        return OpenAIProvider(settings.openai_api_key)
    return OfflineProvider()
