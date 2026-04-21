from sqlalchemy import (
    Column, String, Float, Integer, Text, DateTime,
    Date, ForeignKey, ARRAY, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship, declarative_base
import uuid

Base = declarative_base()


def new_uuid():
    return str(uuid.uuid4())


class Driver(Base):
    __tablename__ = "drivers"

    id              = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    plate_number    = Column(String(20), unique=True, nullable=False, index=True)
    avg_rating      = Column(Float, default=0.0)
    total_reports   = Column(Integer, default=0)
    safe_count      = Column(Integer, default=0)
    safety_status   = Column(String(10), default="unknown")  # safe | caution | danger | unknown
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), onupdate=func.now())

    reports = relationship("Report", back_populates="driver")


class Report(Base):
    __tablename__ = "reports"

    id             = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    driver_id      = Column(UUID(as_uuid=False), ForeignKey("drivers.id"), nullable=False)
    user_id        = Column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    star_rating    = Column(Integer, nullable=False)
    incident_types = Column(ARRAY(String), default=[])
    description    = Column(Text, default="")
    incident_date  = Column(String(100), default="")
    status         = Column(String(10), default="pending")  # pending | approved | rejected
    created_at     = Column(DateTime(timezone=True), server_default=func.now())

    driver = relationship("Driver", back_populates="reports")
    user   = relationship("User", back_populates="reports")


class User(Base):
    __tablename__ = "users"

    id                = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    email             = Column(String(255), unique=True, nullable=False, index=True)
    name              = Column(String(255), nullable=False)
    hashed_password   = Column(String(255), nullable=False)
    plan              = Column(String(10), default="free")   # free | pro
    searches_today    = Column(Integer, default=0)
    search_reset_date = Column(Date, default=func.current_date())
    is_admin          = Column(Integer, default=0)           # 0=rider 1=admin
    created_at        = Column(DateTime(timezone=True), server_default=func.now())

    reports      = relationship("Report", back_populates="user")
    subscription = relationship("Subscription", back_populates="user", uselist=False)


class Subscription(Base):
    __tablename__ = "subscriptions"

    id               = Column(UUID(as_uuid=False), primary_key=True, default=new_uuid)
    user_id          = Column(UUID(as_uuid=False), ForeignKey("users.id"), unique=True, nullable=False)
    plan             = Column(String(10), default="free")
    billing_cycle    = Column(String(10), default="monthly")  # monthly | annual
    status           = Column(String(10), default="trial")    # trial | active | cancelled
    trial_ends_at    = Column(Date, nullable=True)
    next_billing_date = Column(Date, nullable=True)
    created_at       = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="subscription")
