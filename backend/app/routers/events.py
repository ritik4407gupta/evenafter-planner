from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models import Event, User, Task, Vendor, Guest, Expense
from app.schemas import EventCreate, EventOut
from app.dependencies import get_current_user

router = APIRouter(prefix="/api/events", tags=["events"])

def owned_event(db: Session, event_id: int, user: User) -> Event:
    event = db.scalar(select(Event).where(Event.id == event_id, Event.owner_id == user.id))
    if not event:
        raise HTTPException(status_code=404, detail="Event not found.")
    return event

@router.get("", response_model=list[EventOut])
def list_events(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return list(db.scalars(select(Event).where(Event.owner_id == user.id).order_by(Event.created_at.desc())))

@router.post("", response_model=EventOut, status_code=201)
def create_event(payload: EventCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = Event(owner_id=user.id, **payload.model_dump())
    db.add(event); db.commit(); db.refresh(event)
    defaults = [
      ("Decide on your event moodboard", "Planning", 60, "High", "Collect references for colours, florals and the overall feeling."),
      ("Set your guest list first draft", "Guests", 45, "High", "Add the people who matter and leave room for updates."),
      ("Shortlist three venues", "Venue", 40, "Urgent", "Compare capacity, accessibility, inclusions and cancellation terms."),
      ("Build your vendor shortlist", "Vendors", 30, "Medium", "Gather comparable quotes before making any commitments."),
      ("Choose a menu direction", "Catering", 21, "Medium", "Balance dietary needs, service style and your budget."),
      ("Send invitations", "Guests", 14, "High", "Include event time, location, RSVP date and useful travel details."),
    ]
    for idx, (title, category, weeks, priority, description) in enumerate(defaults):
        from datetime import timedelta
        due = event.event_date - timedelta(days=weeks * 7) if event.event_date else None
        db.add(Task(event_id=event.id, title=title, category=category, due_date=due, priority=priority, status="To do", description=description, sort_order=idx))
    allocations = [("Venue", .25, "#D98D87"), ("Food & drinks", .21, "#D5B17B"), ("Photography", .12, "#9BAE9D"), ("Florals & decor", .14, "#B7A1C9"), ("Outfits", .10, "#C9A4A0"), ("Music & extras", .08, "#8EA8B7"), ("Buffer", .10, "#D8D5CE")]
    for category, share, color in allocations:
        db.add(Expense(event_id=event.id, category=category, planned=round(event.budget * share), spent=0, color=color))
    db.commit(); db.refresh(event)
    return event

@router.get("/{event_id}", response_model=EventOut)
def get_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return owned_event(db, event_id, user)

@router.patch("/{event_id}", response_model=EventOut)
def update_event(event_id: int, payload: EventCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = owned_event(db, event_id, user)
    previous_date = event.event_date
    previous_budget = event.budget
    for key, value in payload.model_dump().items():
        setattr(event, key, value)
    # If the event date moves, shift existing task deadlines by the same amount
    # so tasks retain their relative lead time rather than being silently reset.
    if previous_date and event.event_date and previous_date != event.event_date:
        from datetime import timedelta
        shift = (event.event_date - previous_date).days
        for task in event.tasks:
            if task.due_date:
                task.due_date = task.due_date + timedelta(days=shift)
    # When the total budget changes, resize the current category allocations
    # proportionally. Users can then fine-tune individual categories in Budget.
    if previous_budget != event.budget and event.expenses:
        total_planned = sum(max(0, row.planned) for row in event.expenses)
        if total_planned > 0:
            allocated = 0.0
            for row in event.expenses[:-1]:
                row.planned = round(event.budget * max(0, row.planned) / total_planned, 2)
                allocated += row.planned
            event.expenses[-1].planned = round(max(0, event.budget - allocated), 2)
    db.commit(); db.refresh(event)
    return event

@router.delete("/{event_id}", status_code=204)
def delete_event(event_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    event = owned_event(db, event_id, user)
    db.delete(event); db.commit()
