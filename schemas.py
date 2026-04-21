from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime, date


# ── Auth ──────────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    name:     str        = Field(..., min_length=2)
    email:    EmailStr
    password: str        = Field(..., min_length=6)

class LoginRequest(BaseModel):
    email:    EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type:   str = "bearer"
    user_id:      str
    name:         str
    plan:         str


# ── Drivers ───────────────────────────────────────────────────────────────────

class DriverPublic(BaseModel):
    id:            str
    plate_number:  str
    avg_rating:    float
    total_reports: int
    safe_count:    int
    safety_status: str

    class Config:
        from_attributes = True


# ── Reports ───────────────────────────────────────────────────────────────────

class ReportCreate(BaseModel):
    plate_number:   str            = Field(..., min_length=4)
    star_rating:    int            = Field(..., ge=1, le=5)
    incident_types: List[str]      = []
    description:    str            = ""
    incident_date:  str            = ""

class ReportPublic(BaseModel):
    id:             str
    star_rating:    int
    incident_types: List[str]
    description:    str
    incident_date:  str
    status:         str
    created_at:     datetime

    class Config:
        from_attributes = True

class ReportWithDriver(ReportPublic):
    plate_number: str


# ── Search result ─────────────────────────────────────────────────────────────

class SearchResult(BaseModel):
    found:         bool
    plate_number:  str
    safety_status: str
    avg_rating:    float
    total_reports: int
    safe_pct:      int
    tags:          List[str]
    reviews:       List[dict]


# ── Subscriptions ─────────────────────────────────────────────────────────────

class SubscribeRequest(BaseModel):
    billing_cycle: str = "monthly"   # monthly | annual

class SubscriptionResponse(BaseModel):
    plan:              str
    billing_cycle:     str
    status:            str
    trial_ends_at:     Optional[date]
    next_billing_date: Optional[date]

    class Config:
        from_attributes = True


# ── Admin ─────────────────────────────────────────────────────────────────────

class ReviewAction(BaseModel):
    action: str   # approve | reject
