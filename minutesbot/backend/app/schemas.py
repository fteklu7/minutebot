from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field


class ActionItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    meeting_id: int
    task: str
    owner: str | None
    due_date: date | None
    done: bool


class ActionItemPatch(BaseModel):
    task: str | None = Field(default=None, min_length=1, max_length=1000)
    owner: str | None = Field(default=None, max_length=100)
    due_date: date | None = None
    done: bool | None = None


class MeetingSummary(BaseModel):
    id: int
    title: str
    meeting_date: date
    status: str
    open_items: int
    created_at: datetime


class MeetingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    meeting_date: date
    status: str
    error: str | None
    summary: str | None
    decisions: list[str]
    transcript: str | None
    action_items: list[ActionItemOut]


class SearchResult(BaseModel):
    meeting_id: int
    meeting_title: str
    meeting_date: date
    text: str
    score: float
