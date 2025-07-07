# Add these imports at the top of your file
from sqlalchemy import Column, String, DateTime
from sqlalchemy.sql import func
from backend.database import Base

# Define the Booking model for the database
class BookingModel(Base):
    __tablename__ = "bookings"  

    id = Column(String, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, index=True)
    schedule_date = Column(String, index=True)
    schedule_time = Column(String, index=True)
    created_at = Column(DateTime(timezone=True), nullable=True)




