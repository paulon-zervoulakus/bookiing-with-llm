# appointment_routes.py - Appointment routes
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from datetime import datetime
from backend.utils.authenticationUtils import AuthUser, get_current_user
from backend.schema.booking_schema import AppointmentCreateSchema, AppointmentResponseSchema, BookingSchema
from backend.database import get_db, Session
# from backend.repositories.booking_repository import BookingRepository
from backend.services.booking_service import BookingService
router = APIRouter(prefix="/api/appointments", tags=["appointments"])

@router.get("", response_model=List[BookingSchema])
async def get_appointments(
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
# async def get_appointments():
    """Get user's appointments (requires authentication)"""

    booking_service = BookingService(db)
    bookings = booking_service.get_booking_service()


    # This is where you'd query your database
    # For now, returning mock data filtered by user
    # mock_bookings = [
    #     BookingSchema(
    #         id= 1,
    #         name= "John Doe",
    #         email= current_user.email,
    #         date= "2024-12-15",
    #         time= "10:00",
    #         # "duration": 60,
    #         # "description": "Annual checkup",
    #         # "created_at": "2024-12-01T10:00:00Z"
    #     )
    # ]
    
    # Filter appointments by current user
    # user_appointments = [
    #     apt for apt in mock_bookings
    #     if apt["user_email"] == current_user.email
    # ]
    
    return bookings

@router.post("", response_model=BookingSchema)
async def create_appointment(
    appointment: BookingSchema,  # Schema validation happens here
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        new_booking = BookingService(db).create_booking(appointment)
        return new_booking
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.delete("/{appointment_id}")
async def delete_appointment(
    appointment_id: str,
    current_user: AuthUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete appointment (requires authentication and ownership)"""
    # This is where you'd check if the appointment belongs to the user
    # and delete it from your database

    to_delete = BookingService(db)
    if to_delete.delete_appointment(appointment_id):
        return {
            "status": "success",
            "message": "Appointment deleted successfully"
        }
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or you don't have permission to delete it"
        )

@router.put("/{appointment_id}", response_model=AppointmentResponseSchema)
async def update_appointment(
    appointment_id: int,
    appointment: AppointmentCreateSchema,
    current_user: AuthUser = Depends(get_current_user)
):
    """Update appointment (requires authentication and ownership)"""
    # This is where you'd check ownership and update in your database
    
    # Mock logic - in real app, query and update database
    if appointment_id == 1:  # Mock check
        updated_appointment = {
            "id": appointment_id,
            "title": appointment.title,
            "date": appointment.date,
            "time": appointment.time,
            "duration": appointment.duration,
            "description": appointment.description,
            "user_email": current_user.email,
            "created_at": "2024-12-01T10:00:00Z"  # Keep original creation time
        }
        return updated_appointment
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Appointment not found or you don't have permission to update it"
        )