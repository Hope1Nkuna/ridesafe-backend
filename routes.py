from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import Driver, Report, User, Subscription
from schemas import (
    RegisterRequest, LoginRequest, TokenResponse,
    ReportCreate, ReportPublic, ReportWithDriver,
    SearchResult, SubscribeRequest, SubscriptionResponse,
    ReviewAction,
)
from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin,
)
from utils import (
    recalculate_driver_score, check_search_limit,
    increment_search_count, build_tags, format_reviews,
)

router = APIRouter()


# ── AUTH ──────────────────────────────────────────────────────────────────────

@router.post("/auth/register", response_model=TokenResponse, tags=["Auth"])
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        plan=user.plan,
    )


@router.post("/auth/login", response_model=TokenResponse, tags=["Auth"])
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token({"sub": user.id})
    return TokenResponse(
        access_token=token,
        user_id=user.id,
        name=user.name,
        plan=user.plan,
    )


# ── SEARCH ────────────────────────────────────────────────────────────────────

@router.get("/search/{plate}", response_model=SearchResult, tags=["Search"])
def search_plate(
    plate: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plate = plate.upper().strip()

    if not check_search_limit(current_user, db):
        raise HTTPException(
            status_code=429,
            detail="Daily search limit reached. Upgrade to Rider Pro for unlimited searches.",
        )

    driver = db.query(Driver).filter(Driver.plate_number == plate).first()

    if not driver:
        increment_search_count(current_user, db)
        return SearchResult(
            found=False,
            plate_number=plate,
            safety_status="unknown",
            avg_rating=0.0,
            total_reports=0,
            safe_pct=0,
            tags=[],
            reviews=[],
        )

    approved_reports = (
        db.query(Report)
        .filter(Report.driver_id == driver.id, Report.status == "approved")
        .order_by(Report.created_at.desc())
        .all()
    )

    safe_pct = (
        round((driver.safe_count / driver.total_reports) * 100)
        if driver.total_reports > 0 else 0
    )

    increment_search_count(current_user, db)

    return SearchResult(
        found=True,
        plate_number=plate,
        safety_status=driver.safety_status,
        avg_rating=driver.avg_rating,
        total_reports=driver.total_reports,
        safe_pct=safe_pct,
        tags=build_tags(approved_reports),
        reviews=format_reviews(approved_reports),
    )


# ── REPORTS ───────────────────────────────────────────────────────────────────

@router.post("/reports", response_model=ReportPublic, tags=["Reports"])
def submit_report(
    body: ReportCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    plate = body.plate_number.upper().strip()

    # Get or create the driver record
    driver = db.query(Driver).filter(Driver.plate_number == plate).first()
    if not driver:
        driver = Driver(plate_number=plate)
        db.add(driver)
        db.commit()
        db.refresh(driver)

    report = Report(
        driver_id=driver.id,
        user_id=current_user.id,
        star_rating=body.star_rating,
        incident_types=body.incident_types,
        description=body.description,
        incident_date=body.incident_date,
        status="pending",
    )
    db.add(report)
    db.commit()
    db.refresh(report)
    return report


@router.get("/reports/my", response_model=list[ReportWithDriver], tags=["Reports"])
def my_reports(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reports = (
        db.query(Report, Driver.plate_number)
        .join(Driver, Report.driver_id == Driver.id)
        .filter(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .all()
    )
    result = []
    for report, plate in reports:
        r = ReportWithDriver.model_validate(report)
        r.plate_number = plate
        result.append(r)
    return result


# ── SUBSCRIPTIONS ─────────────────────────────────────────────────────────────

@router.post("/subscribe", response_model=SubscriptionResponse, tags=["Subscriptions"])
def subscribe(
    body: SubscribeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.plan == "pro":
        raise HTTPException(status_code=400, detail="Already on Rider Pro")

    trial_end    = date.today() + timedelta(days=7)
    billing_date = trial_end + timedelta(days=1)

    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if sub:
        sub.plan              = "pro"
        sub.billing_cycle     = body.billing_cycle
        sub.status            = "trial"
        sub.trial_ends_at     = trial_end
        sub.next_billing_date = billing_date
    else:
        sub = Subscription(
            user_id=current_user.id,
            plan="pro",
            billing_cycle=body.billing_cycle,
            status="trial",
            trial_ends_at=trial_end,
            next_billing_date=billing_date,
        )
        db.add(sub)

    current_user.plan = "pro"
    db.commit()
    db.refresh(sub)
    return sub


@router.delete("/subscribe", tags=["Subscriptions"])
def cancel_subscription(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sub = db.query(Subscription).filter(Subscription.user_id == current_user.id).first()
    if not sub:
        raise HTTPException(status_code=404, detail="No active subscription")

    sub.status        = "cancelled"
    current_user.plan = "free"
    db.commit()
    return {"message": "Subscription cancelled. You keep Pro until the end of your billing period."}


# ── ADMIN ─────────────────────────────────────────────────────────────────────

@router.get("/admin/reports/pending", response_model=list[ReportWithDriver], tags=["Admin"])
def pending_reports(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(Report, Driver.plate_number)
        .join(Driver, Report.driver_id == Driver.id)
        .filter(Report.status == "pending")
        .order_by(Report.created_at.asc())
        .all()
    )
    result = []
    for report, plate in rows:
        r = ReportWithDriver.model_validate(report)
        r.plate_number = plate
        result.append(r)
    return result


@router.patch("/admin/reports/{report_id}", tags=["Admin"])
def review_report(
    report_id: str,
    body: ReviewAction,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    if body.action not in ("approve", "reject"):
        raise HTTPException(status_code=400, detail="action must be 'approve' or 'reject'")

    report = db.query(Report).filter(Report.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    report.status = "approved" if body.action == "approve" else "rejected"
    db.commit()

    driver = db.query(Driver).filter(Driver.id == report.driver_id).first()
    recalculate_driver_score(driver, db)

    return {"message": f"Report {body.action}d. Driver score updated."}
