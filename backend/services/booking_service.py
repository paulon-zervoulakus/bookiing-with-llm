import uuid
from datetime import datetime, timezone
from backend.repositories.booking_repository import BookingRepository
from fastapi import Depends, HTTPException
from backend.schema.booking_schema import BookingSchema
from backend.model.booking import BookingModel
from sqlalchemy.orm import Session
from typing import List

class BookingService:
    def __init__(self, db: Session):
        self.repository = BookingRepository(db)

    def create_booking(self, booking: BookingSchema) -> BookingSchema:
        """Create a new booking with validation"""
        # # Check for existing bookings
        # existing_booking = self.repository.get_by_id() .query(booking).filter(
        #     booking.schedule_date == booking.schedule_date,
        #     booking.schedule_time == booking.schedule_time
        # ).first()
        #
        # if existing_booking:
        #     raise HTTPException(status_code=400, detail="Slot already booked")

        # Create new booking
        new_booking = self.repository.save(
            BookingModel(
                id=str(uuid.uuid4()),
                name=booking.name,
                email=booking.email,
                schedule_date=booking.schedule_date,
                schedule_time=booking.schedule_time,
                created_at=datetime.now(timezone.utc)

            )
        )
        return new_booking

    def get_booking_service(self) -> List[BookingSchema]:
        return self.repository.get_all()

    def delete_appointment(self, apppointment_id: str) -> bool:
        return self.repository.delete(apppointment_id)