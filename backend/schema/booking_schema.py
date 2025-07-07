from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class BookingSchema(BaseModel):
    id: Optional[str] = None
    name: str
    email: str
    schedule_date: str
    schedule_time: str
    created_at: Optional[datetime] = None

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



