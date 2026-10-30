import os
from contextlib import asynccontextmanager
from datetime import date, timedelta
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from app.config import settings
from app.database import Base, engine, SessionLocal, get_db
from app.dependencies import get_current_user
from app.models import User, Event, Task, Vendor, Guest, Expense, UserAIProviderKeys
from app.security import hash_password
from app.routers import auth, events, workspace, ai

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    # Seed demo data in development, or on Vercel/serverless if the database is fresh
    if settings.environment == "development" or os.environ.get("VERCEL"):
        seed_demo_data()
    yield

def seed_demo_data():
    db = SessionLocal()
    try:
        demo_email = "hello@everafter.app"
        user = db.scalar(select(User).where(User.email == demo_email))
        if user:
            return
        user = User(name="Avery Morgan", email=demo_email, password_hash=hash_password("EverAfter2026!"))
        db.add(user); db.flush()
        event_date = date.today() + timedelta(days=143)
        event = Event(owner_id=user.id, title="Avery & Jordan's Wedding", event_type="Wedding", event_date=event_date,
          venue="The Glasshouse Gardens", location="Gurugram, India", guest_count=148, budget=1250000,
          theme="Blush garden soirée", notes="Garden ceremony, warm candlelight, seasonal flowers, thoughtful guest experience.")
        db.add(event); db.flush()
        starter_tasks = [
          ("Lock in the ceremony venue", "Venue", 120, "Urgent", "Confirm inclusions, rain backup, capacity and cancellation terms.", "Done"),
          ("Collect photographer portfolios", "Photography", 105, "High", "Compare style, coverage hours, deliverables and travel costs.", "Done"),
          ("Book a tasting appointment", "Catering", 70, "High", "Check vegetarian options, allergies, serving plan and staffing.", "In progress"),
          ("Choose the ceremony florals", "Florals", 55, "Medium", "Ask about seasonal substitutions and repurposing arrangements.", "To do"),
          ("Send the save-the-dates", "Guests", 45, "High", "Double-check names, addresses, date and RSVP link.", "To do"),
          ("Build the music timeline", "Entertainment", 30, "Medium", "Include entrance cues, special dances, speeches and the final song.", "To do"),
          ("Confirm transport and accessibility", "Logistics", 21, "High", "Share practical arrival details and identify an accessible route.", "To do"),
          ("Prepare the day-of emergency kit", "Final checks", 3, "Low", "Include pins, tape, stain wipes, water, chargers and contact sheet.", "To do"),
        ]
        for i, (title, category, days, priority, description, status) in enumerate(starter_tasks):
            db.add(Task(event_id=event.id, title=title, category=category, due_date=event_date-timedelta(days=days), priority=priority, status=status, description=description, sort_order=i))
        vendors = [
          ("Bloom & Wild Studio", "Florist", 98000, "Shortlisted", 4.8, "hello@bloomwild.example", "Seasonal garden palette; sample proposal pending."),
          ("Golden Hour Stories", "Photography", 145000, "Booked", 4.9, "studio@goldenhour.example", "Coverage and deliverables to be reconfirmed."),
          ("The Whisk Room", "Cake", 22000, "Contacted", 4.7, "orders@whiskroom.example", "Tasting requested; prices are demo data."),
        ]
        for item in vendors: db.add(Vendor(event_id=event.id, name=item[0], category=item[1], quote=item[2], status=item[3], rating=item[4], contact=item[5], notes=item[6]))
        for name, group, rsvp, dietary in [("Maya Patel", "Family", "Confirmed", "Vegetarian"), ("Noah Williams", "Friends", "Confirmed", ""), ("Priya Sharma", "Family", "Pending", "Jain"), ("Leo Chen", "Friends", "Pending", "Nut allergy"), ("Isabella Khan", "Work", "Declined", "")]:
            db.add(Guest(event_id=event.id, name=name, group_name=group, rsvp=rsvp, dietary=dietary))
        for category, planned, spent, color in [("Venue", 310000, 155000, "#D98D87"), ("Food & drinks", 260000, 42000, "#D5B17B"), ("Photography", 145000, 145000, "#9BAE9D"), ("Florals & decor", 180000, 55000, "#B7A1C9"), ("Outfits", 125000, 28000, "#C9A4A0"), ("Music & extras", 105000, 18000, "#8EA8B7"), ("Buffer", 125000, 0, "#D8D5CE")]:
            db.add(Expense(event_id=event.id, category=category, planned=planned, spent=spent, color=color))
        db.commit()
    finally:
        db.close()

app = FastAPI(title=settings.app_name, version="1.0.0", description="Event planning workspace with guarded AI plan drafts.", lifespan=lifespan)
_cors_origins = [o.strip() for o in settings.frontend_origin.split(",") if o.strip()] + ["http://127.0.0.1:5173", "http://localhost:5173", "https://evenafter-planner.vercel.app"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(_cors_origins)),
    allow_origin_regex=r"https://.*(\.vercel\.app|\.onrender\.com)|http://(localhost|127\.0\.0\.1)(:\d+)?",
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)
app.include_router(auth.router); app.include_router(events.router); app.include_router(workspace.router); app.include_router(ai.router)

@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name, "ai_mode": "per-account-provider-keys"}

@app.get("/api/dashboard/{event_id}")
def dashboard(event_id: int, db=Depends(get_db), user=Depends(get_current_user)):
    event = db.scalar(select(Event).where(Event.id == event_id, Event.owner_id == user.id))
    if not event: raise HTTPException(status_code=404, detail="Event not found.")
    tasks = list(db.scalars(select(Task).where(Task.event_id == event_id)))
    guests = list(db.scalars(select(Guest).where(Guest.event_id == event_id)))
    vendors = list(db.scalars(select(Vendor).where(Vendor.event_id == event_id)))
    expenses = list(db.scalars(select(Expense).where(Expense.event_id == event_id)))
    total_planned = sum(e.planned for e in expenses)
    total_spent = sum(e.spent for e in expenses)
    return {"event": {"id": event.id, "title": event.title, "event_type": event.event_type, "event_date": event.event_date, "venue": event.venue, "location": event.location, "guest_count": event.guest_count, "budget": event.budget, "theme": event.theme},
      "tasks": {"total": len(tasks), "completed": sum(t.status == "Done" for t in tasks), "upcoming": sum(t.status != "Done" and t.due_date is not None and t.due_date >= date.today() for t in tasks)},
      "guests": {"total": len(guests), "confirmed": sum(g.rsvp == "Confirmed" for g in guests), "pending": sum(g.rsvp == "Pending" for g in guests)},
      "vendors": {"total": len(vendors), "booked": sum(v.status == "Booked" for v in vendors)},
      "budget": {"limit": event.budget, "planned": total_planned, "spent": total_spent, "remaining": event.budget - total_spent, "percent_spent": round(total_spent / event.budget * 100, 1) if event.budget else 0},
      "expenses": [{"category": e.category, "planned": e.planned, "spent": e.spent, "color": e.color} for e in expenses],
      "next_tasks": [{"id": t.id, "title": t.title, "category": t.category, "due_date": t.due_date, "priority": t.priority, "status": t.status} for t in sorted([x for x in tasks if x.status != "Done"], key=lambda x: x.due_date or date.max)[:5]]}
