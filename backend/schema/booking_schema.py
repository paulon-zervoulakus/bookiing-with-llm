from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class BookingSchema(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    email: Optional[str] = None
    schedule_date: Optional[str] = None
    schedule_time: Optional[str] = None
    created_at: Optional[datetime] = None
    booking_status: Optional[str] = None
    error_message: Optional[str] = None

class AppointmentCreateSchema(BaseModel):
    title: str
    schedule_date: str
    schedule_time: str
    duration: int
    description: Optional[str] = None

class AppointmentResponseSchema(BaseModel):
    id: Optional[int] = None
    title: str
    schedule_date: str
    schecule_time: str
    duration: int
    description: Optional[str]
    user_email: str
    created_at: str

class AvailableSlotsResponseSchema(BaseModel):
    date: str
    slots: list[str]
    user_preferences: Optional[Dict[str, Any]] = None



