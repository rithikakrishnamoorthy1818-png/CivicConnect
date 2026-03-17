from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from .database import Base

class Citizen(Base):
    __tablename__ = "citizens"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    points = Column(Integer, default=0)
    level = Column(String, default="Bronze")
    streak_days = Column(Integer, default=0)
    last_reported = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    complaints = relationship("Complaint", back_populates="citizen")
    vouchers = relationship("Voucher", back_populates="citizen")
    point_logs = relationship("PointLog", back_populates="citizen")

class Admin(Base):
    __tablename__ = "admins"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    department = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

class Complaint(Base):
    __tablename__ = "complaints"
    id = Column(Integer, primary_key=True, index=True)
    citizen_id = Column(Integer, ForeignKey("citizens.id"))
    category = Column(String)
    description = Column(String)
    photo_url = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)
    status = Column(String, default="Pending") # Pending, In-Progress, Resolved, Breach
    current_stage = Column(Integer, default=0)
    stage_timestamps = Column(JSON, default=lambda: {}) # {stage_idx: timestamp}
    stage_marked_by = Column(JSON, default=lambda: {}) # {stage_idx: admin_id}
    ai_detected = Column(Boolean, default=False)
    ai_confidence = Column(Float, nullable=True)
    severity = Column(String) # Low, Medium, High, Critical
    priority_boosted = Column(Boolean, default=False)
    upvotes = Column(Integer, default=0)
    sla_deadline = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

    citizen = relationship("Citizen", back_populates="complaints")
    team = relationship("Team", back_populates="complaint", uselist=False)

class Worker(Base):
    __tablename__ = "workers"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String)
    department = Column(String)
    phone = Column(String)
    status = Column(String, default="free") # free, busy, off_duty
    active_job_count = Column(Integer, default=0)
    avg_resolution_hours = Column(Float, default=0.0)

class Team(Base):
    __tablename__ = "teams"
    id = Column(Integer, primary_key=True, index=True)
    complaint_id = Column(Integer, ForeignKey("complaints.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    complaint = relationship("Complaint", back_populates="team")
    members = relationship("TeamMember", back_populates="team")

class TeamMember(Base):
    __tablename__ = "team_members"
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"))
    worker_id = Column(Integer, ForeignKey("workers.id"))
    role = Column(String) # lead, worker

    team = relationship("Team", back_populates="members")

class Voucher(Base):
    __tablename__ = "vouchers"
    id = Column(Integer, primary_key=True, index=True)
    citizen_id = Column(Integer, ForeignKey("citizens.id"))
    type = Column(String) # bus_1day, bus_7day
    qr_code = Column(String, default=lambda: str(uuid.uuid4()))
    status = Column(String, default="active") # active, used, expired
    generated_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)

    citizen = relationship("Citizen", back_populates="vouchers")

class PointLog(Base):
    __tablename__ = "point_log"
    id = Column(Integer, primary_key=True, index=True)
    citizen_id = Column(Integer, ForeignKey("citizens.id"))
    action = Column(String)
    points_earned = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

    citizen = relationship("Citizen", back_populates="point_logs")

class Redemption(Base):
    __tablename__ = "redemptions"
    id = Column(Integer, primary_key=True, index=True)
    citizen_id = Column(Integer, ForeignKey("citizens.id"))
    reward_type = Column(String)
    points_cost = Column(Integer)
    status = Column(String, default="completed")
    requested_at = Column(DateTime, default=datetime.utcnow)
