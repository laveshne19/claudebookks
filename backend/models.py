"""Pydantic models for Nalanda ERP."""
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from typing import List, Optional, Literal
from datetime import datetime, timezone
import uuid


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id() -> str:
    return str(uuid.uuid4())


Role = Literal["super_admin", "admin", "manager", "sales", "accounts"]


# ====== AUTH ======
class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    role: Role = "sales"
    phone: Optional[str] = None
    territory: Optional[str] = None


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    phone: Optional[str] = None
    territory: Optional[str] = None
    created_at: Optional[str] = None
    active: bool = True


# ====== CUSTOMER ======
class CustomerCreate(BaseModel):
    name: str
    code: Optional[str] = None
    area: str
    city: str = "Mumbai"
    state: str = "Maharashtra"
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    gstin: Optional[str] = None
    credit_limit: float = 0.0
    brand_preferences: List[str] = []
    assigned_to: Optional[str] = None  # user id
    lat: Optional[float] = None
    lng: Optional[float] = None


class Customer(CustomerCreate):
    id: str = Field(default_factory=new_id)
    outstanding: float = 0.0
    overdue: float = 0.0
    last_payment_date: Optional[str] = None
    last_visit_date: Optional[str] = None
    last_order_date: Optional[str] = None
    total_purchases: float = 0.0
    credit_risk_score: int = 50  # 0-100
    payment_behaviour_score: int = 50  # 0-100
    created_at: str = Field(default_factory=now_iso)


# ====== INVOICE ======
class InvoiceLineItem(BaseModel):
    sku: str
    product: str
    brand: str
    qty: int
    unit_price: float
    amount: float


class InvoiceCreate(BaseModel):
    customer_id: str
    invoice_no: Optional[str] = None
    date: str
    due_date: str
    items: List[InvoiceLineItem] = []
    amount: float
    paid_amount: float = 0.0
    status: Literal["paid", "partial", "unpaid", "overdue"] = "unpaid"
    brand: Optional[str] = None


class Invoice(InvoiceCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_iso)


# ====== PAYMENT ======
class PaymentCreate(BaseModel):
    customer_id: str
    invoice_id: Optional[str] = None
    amount: float
    date: str
    method: Literal["cash", "neft", "rtgs", "upi", "cheque"] = "neft"
    reference: Optional[str] = None
    notes: Optional[str] = None


class Payment(PaymentCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_iso)


# ====== SCHEME ======
class SchemeCreate(BaseModel):
    name: str
    brand: str
    type: Literal["volume", "value", "product", "incentive"] = "value"
    description: str = ""
    start_date: str
    end_date: str
    target_amount: float = 0.0
    reward: str = ""
    active: bool = True


class Scheme(SchemeCreate):
    id: str = Field(default_factory=new_id)
    progress: float = 0.0
    created_at: str = Field(default_factory=now_iso)


# ====== TARGET ======
class TargetCreate(BaseModel):
    user_id: str
    period: str  # e.g. "2026-02"
    target_amount: float
    target_collection: float = 0.0


class Target(TargetCreate):
    id: str = Field(default_factory=new_id)
    achieved_amount: float = 0.0
    collected_amount: float = 0.0
    created_at: str = Field(default_factory=now_iso)


# ====== NOTIFICATION ======
class NotificationCreate(BaseModel):
    user_id: Optional[str] = None  # None means broadcast
    title: str
    body: str
    type: Literal["overdue", "scheme", "task", "announcement", "followup", "system"] = "system"
    link: Optional[str] = None


class Notification(NotificationCreate):
    id: str = Field(default_factory=new_id)
    read: bool = False
    created_at: str = Field(default_factory=now_iso)


# ====== TASK ======
class TaskCreate(BaseModel):
    assigned_to: str
    customer_id: Optional[str] = None
    title: str
    description: Optional[str] = ""
    due_date: str
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    status: Literal["open", "in_progress", "done", "cancelled"] = "open"


class Task(TaskCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_iso)


# ====== VISIT ======
class VisitCreate(BaseModel):
    user_id: str
    customer_id: str
    date: str
    duration_minutes: int = 0
    notes: Optional[str] = ""
    lat: Optional[float] = None
    lng: Optional[float] = None
    outcome: Literal["sale", "followup", "collection", "no_response"] = "followup"


class Visit(VisitCreate):
    id: str = Field(default_factory=new_id)
    created_at: str = Field(default_factory=now_iso)


# ====== AI ======
class AIInsightResponse(BaseModel):
    customer_id: str
    summary: str
    predicted_next_order: str
    credit_risk_score: int
    payment_behaviour_score: int
    recovery_approach: str
    upsell_suggestions: List[str]
    pitch_points: List[str]
    best_visit_time: str
    generated_at: str
