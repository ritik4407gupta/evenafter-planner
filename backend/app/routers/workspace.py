from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.database import get_db
from app.models import Event, Task, Vendor, Guest, Expense, User
from app.schemas import TaskCreate, TaskUpdate, TaskOut, VendorCreate, VendorOut, GuestCreate, GuestOut, ExpenseCreate, ExpenseUpdate, ExpenseOut
from app.dependencies import get_current_user

router = APIRouter(prefix="/api", tags=["workspace"])

def require_event(db: Session, event_id: int, user: User):
    event = db.scalar(select(Event).where(Event.id == event_id, Event.owner_id == user.id))
    if not event: raise HTTPException(status_code=404, detail="Event not found.")
    return event

def own_resource(db: Session, model, item_id: int, user: User):
    item = db.get(model, item_id)
    if not item: raise HTTPException(status_code=404, detail="Item not found.")
    require_event(db, item.event_id, user)
    return item

@router.get("/tasks", response_model=list[TaskOut])
def list_tasks(event_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_event(db, event_id, user)
    return list(db.scalars(select(Task).where(Task.event_id == event_id).order_by(Task.sort_order, Task.due_date)))

@router.post("/tasks", response_model=TaskOut, status_code=201)
def create_task(payload: TaskCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_event(db, payload.event_id, user)
    item = Task(**payload.model_dump())
    db.add(item); db.commit(); db.refresh(item); return item

@router.patch("/tasks/{item_id}", response_model=TaskOut)
def update_task(item_id: int, payload: TaskUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = own_resource(db, Task, item_id, user)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item

@router.delete("/tasks/{item_id}", status_code=204)
def delete_task(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = own_resource(db, Task, item_id, user); db.delete(item); db.commit()

@router.get("/vendors", response_model=list[VendorOut])
def list_vendors(event_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_event(db, event_id, user); return list(db.scalars(select(Vendor).where(Vendor.event_id == event_id).order_by(Vendor.id.desc())))

@router.post("/vendors", response_model=VendorOut, status_code=201)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_event(db, payload.event_id, user); item = Vendor(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@router.patch("/vendors/{item_id}", response_model=VendorOut)
def update_vendor(item_id: int, payload: VendorCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = own_resource(db, Vendor, item_id, user)
    for key, value in payload.model_dump(exclude={"event_id"}).items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item

@router.delete("/vendors/{item_id}", status_code=204)
def delete_vendor(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = own_resource(db, Vendor, item_id, user); db.delete(item); db.commit()

@router.get("/guests", response_model=list[GuestOut])
def list_guests(event_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_event(db, event_id, user); return list(db.scalars(select(Guest).where(Guest.event_id == event_id).order_by(Guest.name)))

@router.post("/guests", response_model=GuestOut, status_code=201)
def create_guest(payload: GuestCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_event(db, payload.event_id, user); item = Guest(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@router.patch("/guests/{item_id}", response_model=GuestOut)
def update_guest(item_id: int, payload: GuestCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = own_resource(db, Guest, item_id, user)
    for key, value in payload.model_dump(exclude={"event_id"}).items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item

@router.delete("/guests/{item_id}", status_code=204)
def delete_guest(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = own_resource(db, Guest, item_id, user); db.delete(item); db.commit()

@router.get("/expenses", response_model=list[ExpenseOut])
def list_expenses(event_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_event(db, event_id, user); return list(db.scalars(select(Expense).where(Expense.event_id == event_id).order_by(Expense.id)))

@router.post("/expenses", response_model=ExpenseOut, status_code=201)
def create_expense(payload: ExpenseCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    require_event(db, payload.event_id, user); item = Expense(**payload.model_dump()); db.add(item); db.commit(); db.refresh(item); return item

@router.patch("/expenses/{item_id}", response_model=ExpenseOut)
def update_expense(item_id: int, payload: ExpenseUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = own_resource(db, Expense, item_id, user)
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(item, key, value)
    db.commit(); db.refresh(item); return item

@router.delete("/expenses/{item_id}", status_code=204)
def delete_expense(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    item = own_resource(db, Expense, item_id, user); db.delete(item); db.commit()
