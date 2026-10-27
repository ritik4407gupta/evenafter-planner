from datetime import date
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Literal

class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class LoginInput(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

class UserOut(BaseModel):
    id: int
    name: str
    email: EmailStr
    model_config = ConfigDict(from_attributes=True)

class AuthOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

class EventCreate(BaseModel):
    title: str = Field(min_length=2, max_length=160)
    event_type: Literal["Wedding", "Birthday", "Community", "Anniversary", "Other"] = "Wedding"
    event_date: date | None = None
    venue: str = Field(default="Choose your venue", max_length=200)
    location: str = Field(default="Not set yet", max_length=160)
    guest_count: int = Field(default=120, ge=1, le=10000)
    budget: float = Field(default=250000, ge=0, le=100000000)
    theme: str = Field(default="Garden romance", max_length=80)
    notes: str = Field(default="", max_length=4000)

class EventOut(EventCreate):
    id: int
    owner_id: int
    model_config = ConfigDict(from_attributes=True)

class TaskCreate(BaseModel):
    event_id: int
    title: str = Field(min_length=2, max_length=180)
    category: str = Field(default="General", max_length=60)
    due_date: date | None = None
    priority: Literal["Low", "Medium", "High", "Urgent"] = "Medium"
    status: Literal["To do", "In progress", "Done"] = "To do"
    description: str = Field(default="", max_length=2000)

class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=180)
    category: str | None = Field(default=None, max_length=60)
    due_date: date | None = None
    priority: Literal["Low", "Medium", "High", "Urgent"] | None = None
    status: Literal["To do", "In progress", "Done"] | None = None
    description: str | None = Field(default=None, max_length=2000)

class TaskOut(BaseModel):
    id: int
    event_id: int
    title: str
    category: str
    due_date: date | None
    priority: str
    status: str
    description: str
    sort_order: int
    model_config = ConfigDict(from_attributes=True)

class VendorCreate(BaseModel):
    event_id: int
    name: str = Field(min_length=2, max_length=140)
    category: str = Field(min_length=2, max_length=60)
    quote: float = Field(default=0, ge=0, le=100000000)
    status: Literal["Researching", "Contacted", "Shortlisted", "Booked"] = "Researching"
    rating: float = Field(default=0, ge=0, le=5)
    contact: str = Field(default="", max_length=180)
    notes: str = Field(default="", max_length=2000)

class VendorOut(VendorCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class GuestCreate(BaseModel):
    event_id: int
    name: str = Field(min_length=2, max_length=140)
    email: str = Field(default="", max_length=255)
    group_name: str = Field(default="Friends", max_length=80)
    rsvp: Literal["Pending", "Confirmed", "Declined"] = "Pending"
    plus_one: bool = False
    dietary: str = Field(default="", max_length=120)

class GuestOut(GuestCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class ExpenseCreate(BaseModel):
    event_id: int
    category: str = Field(min_length=2, max_length=60)
    planned: float = Field(default=0, ge=0, le=100000000)
    spent: float = Field(default=0, ge=0, le=100000000)
    color: str = Field(default="#D58F7A", pattern=r"^#[0-9a-fA-F]{6}$")

class ExpenseUpdate(BaseModel):
    planned: float | None = Field(default=None, ge=0, le=100000000)
    spent: float | None = Field(default=None, ge=0, le=100000000)

class ExpenseOut(BaseModel):
    id: int
    event_id: int
    category: str
    planned: float
    spent: float
    color: str
    model_config = ConfigDict(from_attributes=True)

class DraftPlanInput(BaseModel):
    event_type: Literal["Wedding", "Birthday", "Community", "Anniversary", "Other"]
    budget: float = Field(ge=0, le=100000000)
    guest_count: int = Field(ge=1, le=10000)
    event_date: date | None = None
    theme: str = Field(min_length=2, max_length=80)
    location: str = Field(default="India", max_length=160)
    priorities: list[str] = Field(default_factory=list, max_length=8)

class DraftTask(BaseModel):
    title: str = Field(min_length=2, max_length=180)
    category: str = Field(max_length=60)
    weeks_before: int = Field(ge=0, le=104)
    priority: Literal["Low", "Medium", "High", "Urgent"]
    description: str = Field(max_length=500)

class DraftPlanOut(BaseModel):
    headline: str = Field(max_length=160)
    summary: str = Field(max_length=900)
    budget_note: str = Field(max_length=400)
    tasks: list[DraftTask] = Field(min_length=3, max_length=15)
    ideas: list[str] = Field(min_length=3, max_length=8)
    assumptions: list[str] = Field(max_length=8)
    generated_by: Literal["gemini", "groq"]

class AssistantTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=1800)

class PlanningAssistantInput(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    event_type: Literal["Wedding", "Birthday", "Community", "Anniversary", "Other"] = "Wedding"
    event_title: str = Field(default="My celebration", max_length=160)
    event_date: date | None = None
    budget: float = Field(default=0, ge=0, le=100000000)
    guest_count: int = Field(default=80, ge=1, le=10000)
    theme: str = Field(default="Thoughtful celebration", max_length=80)
    location: str = Field(default="India", max_length=160)
    notes: str = Field(default="", max_length=2500)
    existing_tasks: list[str] = Field(default_factory=list, max_length=30)
    conversation: list[AssistantTurn] = Field(default_factory=list, max_length=12)

class PlanningAssistantOut(BaseModel):
    reply: str = Field(min_length=1, max_length=1800)
    suggestions: list[str] = Field(min_length=2, max_length=6)
    suggested_tasks: list[DraftTask] = Field(default_factory=list, max_length=6)
    follow_up_questions: list[str] = Field(default_factory=list, max_length=3)
    guardrail_notes: list[str] = Field(default_factory=list, max_length=4)
    generated_by: Literal["gemini", "groq"]


class AIProviderSettingsInput(BaseModel):
    # Blank values preserve an existing key; clear_* is required to delete a saved key.
    gemini_api_key: str | None = Field(default=None, min_length=10, max_length=500)
    groq_api_key: str | None = Field(default=None, min_length=10, max_length=500)
    clear_gemini: bool = False
    clear_groq: bool = False

    @field_validator("gemini_api_key", "groq_api_key")
    @classmethod
    def normalize_api_key(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class AIProviderSettingsOut(BaseModel):
    gemini_configured: bool
    gemini_masked: str | None = None
    groq_configured: bool
    groq_masked: str | None = None
    ai_enabled: bool
    primary_provider: Literal["gemini", "none"]
    fallback_provider: Literal["groq", "none"]
