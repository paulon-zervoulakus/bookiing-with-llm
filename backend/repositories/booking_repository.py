from sqlalchemy.schema import Column
from sqlalchemy.types import Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

from backend.model.booking import BookingModel

class BookingRepository:
    def __init__(self, db):
        self.db = db

    def get_all(self):
        return self.db.query(BookingModel).all()

    def get_by_id(self, booking_id: str):
        return self.db.query(BookingModel).get(booking_id)

    def save(self, booking: BookingModel):
        self.db.add(booking)
        self.db.commit()
        self.db.refresh(booking)
        return booking

    def delete(self, booking_id: str)-> bool:
        try:
            to_delete = self.db.query(BookingModel).filter(BookingModel.id==booking_id).first()
            if to_delete:
                self.db.delete(to_delete)
                self.db.commit()
                return True
            else:
                return False
        except Exception as e:
            return False

    def update(self, booking_id: str, update_data: dict):
        booking = self.db.query(BookingModel).get(booking_id)
        for key, value in update_data.items():
            if hasattr(booking, key):
                setattr(booking, key, value)
        self.db.commit()
        self.db.refresh(booking)
