import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, 
    Text, UniqueConstraint, Index, func
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="PATIENT") # 'PATIENT', 'DOCTOR', 'ADMIN'
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Optional relationship to doctor profile
    doctor_profile: Mapped[Optional["Doctor"]] = relationship("Doctor", back_populates="user", uselist=False)

class Doctor(Base):
    __tablename__ = "doctors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    department: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    specialization: Mapped[str] = mapped_column(String(255), nullable=False)
    room_number: Mapped[str] = mapped_column(String(50), default="OPD-101")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[Optional["User"]] = relationship("User", back_populates="doctor_profile")
    slots: Mapped[List["Slot"]] = relationship("Slot", back_populates="doctor", cascade="all, delete-orphan")
    appointments: Mapped[List["Appointment"]] = relationship("Appointment", back_populates="doctor")

class Slot(Base):
    __tablename__ = "slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    slot_timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    is_booked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    # Strict composite unique constraint: prevents any duplicate booking for same doctor at same timestamp
    __table_args__ = (
        UniqueConstraint("doctor_id", "slot_timestamp", name="uq_doctor_slot_timestamp"),
        Index("idx_doctor_slot_status", "doctor_id", "slot_timestamp", "is_booked"),
    )

    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="slots")
    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment", back_populates="slot", uselist=False)

class Appointment(Base):
    __tablename__ = "appointments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    token_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False) # e.g. CARD-20261020-001
    caller_phone: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    call_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False) # Idempotency key
    patient_name: Mapped[str] = mapped_column(String(255), nullable=False)
    patient_age: Mapped[int] = mapped_column(Integer, nullable=False)
    
    slot_id: Mapped[int] = mapped_column(Integer, ForeignKey("slots.id"), unique=True, nullable=False)
    doctor_id: Mapped[int] = mapped_column(Integer, ForeignKey("doctors.id"), nullable=False, index=True)
    department: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    
    status: Mapped[str] = mapped_column(String(50), default="SCHEDULED") 
    # SCHEDULED, IN_QUEUE, IN_CONSULTATION, COMPLETED, CANCELLED, ESCALATED
    queue_position: Mapped[int] = mapped_column(Integer, default=1)
    booked_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    consultation_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    follow_up_status: Mapped[str] = mapped_column(String(50), default="NOT_TRIGGERED")
    # NOT_TRIGGERED, PENDING, CALLED_RECOVERING, CALLED_WORSENING, ESCALATED_TO_DOCTOR, COMPLETED

    slot: Mapped["Slot"] = relationship("Slot", back_populates="appointment")
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="appointments")
    triage_notes: Mapped[List["TriageNote"]] = relationship("TriageNote", back_populates="appointment", cascade="all, delete-orphan")
    follow_ups: Mapped[List["FollowUpRecord"]] = relationship("FollowUpRecord", back_populates="appointment", cascade="all, delete-orphan")

class TriageNote(Base):
    __tablename__ = "triage_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appointment_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("appointments.id"), nullable=True)
    call_id: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    chief_complaint: Mapped[str] = mapped_column(Text, nullable=False)
    duration: Mapped[str] = mapped_column(String(100), nullable=False)
    severity_scale: Mapped[int] = mapped_column(Integer, nullable=False) # 1-10
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    associated_symptoms: Mapped[str] = mapped_column(Text, default="[]") # JSON stringified
    triage_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    chosen_department: Mapped[str] = mapped_column(String(100), nullable=False)
    department_rationale: Mapped[str] = mapped_column(Text, nullable=False)
    handoff_brief: Mapped[str] = mapped_column(Text, nullable=False)
    urgency_level: Mapped[str] = mapped_column(String(50), default="ROUTINE") # ROUTINE, URGENT, CRITICAL_EMERGENCY
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    appointment: Mapped[Optional["Appointment"]] = relationship("Appointment", back_populates="triage_notes")

class AuditLog(Base):
    """
    Append-only, SHA-256 hash-chained tamper-evident audit log table.
    Every record's record_hash incorporates the previous record's record_hash.
    Any tampering with historical records breaks the hash verification chain.
    """
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    call_id: Mapped[Optional[str]] = mapped_column(String(100), index=True, nullable=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False) # 64-char SHA256
    record_hash: Mapped[str] = mapped_column(String(64), nullable=False) # 64-char SHA256
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

class FollowUpRecord(Base):
    __tablename__ = "follow_up_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    appointment_id: Mapped[int] = mapped_column(Integer, ForeignKey("appointments.id"), nullable=False, index=True)
    call_id: Mapped[str] = mapped_column(String(100), nullable=False)
    scheduled_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    executed_at: Mapped[Optional[datetime.datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    patient_feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recovery_condition: Mapped[str] = mapped_column(String(50), default="PENDING") # PENDING, RECOVERED, IMPROVING, SAME, WORSENING, RED_FLAG
    escalated_to_doctor: Mapped[bool] = mapped_column(Boolean, default=False)
    doctor_alert_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    appointment: Mapped["Appointment"] = relationship("Appointment", back_populates="follow_ups")
