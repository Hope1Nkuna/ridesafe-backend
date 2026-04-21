from datetime import date
from sqlalchemy.orm import Session
from models import Driver, Report, User


FREE_SEARCH_LIMIT = 3


def recalculate_driver_score(driver: Driver, db: Session) -> None:
    """
    Called every time a report is approved or rejected.
    Recomputes avg_rating, total_reports, safe_count, and safety_status
    from all approved reports for this driver.
    """
    approved = (
        db.query(Report)
        .filter(Report.driver_id == driver.id, Report.status == "approved")
        .all()
    )

    total = len(approved)
    if total == 0:
        driver.avg_rating    = 0.0
        driver.total_reports = 0
        driver.safe_count    = 0
        driver.safety_status = "unknown"
        db.commit()
        return

    avg   = sum(r.star_rating for r in approved) / total
    safe  = sum(1 for r in approved if r.star_rating >= 4)
    pct   = (safe / total) * 100

    if pct >= 80:
        status = "safe"
    elif pct >= 50:
        status = "caution"
    else:
        status = "danger"

    driver.avg_rating    = round(avg, 1)
    driver.total_reports = total
    driver.safe_count    = safe
    driver.safety_status = status
    db.commit()


def check_search_limit(user: User, db: Session) -> bool:
    """
    Returns True if the user can perform a search.
    Resets the daily counter if it's a new day.
    Pro users are always allowed.
    """
    if user.plan == "pro":
        return True

    today = date.today()
    if user.search_reset_date != today:
        user.searches_today    = 0
        user.search_reset_date = today
        db.commit()

    return user.searches_today < FREE_SEARCH_LIMIT


def increment_search_count(user: User, db: Session) -> None:
    user.searches_today += 1
    db.commit()


def build_tags(reports: list) -> list:
    """
    Derive community tags from the most common incident types
    across all approved reports.
    """
    from collections import Counter

    label_map = {
        "theft":        "Theft reported",
        "assault":      "Assault reported",
        "kidnap":       "Kidnapping attempt",
        "unsafe":       "Unsafe driving",
        "fraud":        "Fake vehicle / fraud",
        "harassment":   "Harassment reported",
        "overcharge":   "Overcharging",
    }
    positive_tags = ["Friendly", "Professional", "Safe driver", "On time"]

    all_incidents = []
    for r in reports:
        all_incidents.extend(r.incident_types or [])

    if not all_incidents:
        return positive_tags[:3]

    counter = Counter(all_incidents)
    return [label_map[k] for k, _ in counter.most_common(4) if k in label_map]


def format_reviews(reports: list) -> list:
    """Convert approved report rows into the review dicts the app expects."""
    results = []
    for r in reports[:5]:
        tag_map = {
            "theft": "danger", "assault": "danger", "kidnap": "danger",
            "unsafe": "warn",  "fraud": "danger",   "harassment": "warn",
            "overcharge": "warn",
        }
        tags = list({tag_map[i] for i in (r.incident_types or []) if i in tag_map})
        results.append({
            "who":   "Anon rider",
            "when":  r.created_at.strftime("%-d %b %Y") if r.created_at else "",
            "stars": r.star_rating,
            "text":  r.description or "No description provided.",
            "tags":  tags,
        })
    return results
