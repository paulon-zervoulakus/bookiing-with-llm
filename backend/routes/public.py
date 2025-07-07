# public_routes.py - Public routes
from fastapi import APIRouter, Depends
from typing import Optional
from backend.utils.authenticationUtils import AuthUser, get_optional_user
from backend.schema.booking_schema import AvailableSlotsResponseSchema

router = APIRouter(tags=["public"])

@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "message": "Appointment Booking API is running"}

@router.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Appointment Booking API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@router.get("/available-slots", response_model=AvailableSlotsResponseSchema)
async def get_available_slots(
    date: str,
    current_user: Optional[AuthUser] = Depends(get_optional_user)
):
    """Get available time slots (works with or without auth)"""
    # This endpoint can provide different data based on whether user is authenticated
    slots = ["09:00", "10:00", "11:00", "14:00", "15:00", "16:00"]
    
    if current_user:
        # Authenticated users might see more slots or personalized data
        return AvailableSlotsResponseSchema(
            date=date,
            slots=slots,
            user_preferences={"timezone": "UTC", "preferred_duration": 60}
        )
    else:
        # Anonymous users get basic slot information
        return AvailableSlotsResponseSchema(
            date=date, 
            slots=slots
        )