# from backend.services.booking_service import BookingService
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from backend.routes.agent.index import router as agent_router
from backend.routes.auth import router as auth_router
from backend.routes.appointment import router as appointment_router
from backend.routes.public import router as public_router

from backend.database import initialize_chroma_collection, init_db, SessionLocal
from contextlib import asynccontextmanager
from fastapi.responses import JSONResponse
import uvicorn

@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_chroma_collection()
    init_db()
    yield

# Create FastAPI app
app = FastAPI(
    title="Appointment Booking API",
    description="A secure appointment booking system with Google OAuth integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React development server
        "http://localhost:5173",  # Vite development server
        "https://yourdomain.com"  # Production domain
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Typ"],
)

# Include routers
app.include_router(public_router)
app.include_router(agent_router)
app.include_router(auth_router)
app.include_router(appointment_router)

# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "type": "http_exception"
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "status_code": 500,
            "type": "server_error"
        }
    )

# Startup event
# @app.on_event("startup")
# async def startup_event():
#     print("🚀 Appointment Booking API starting up...")
#     print("📖 API Documentation available at: http://localhost:8000/docs")

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

# # In-memory storage
# bookings: List[DTOBooking] = []

# @app.get("/bookings", response_model=List[DTOBooking])
# def get_bookings():
#     db = SessionLocal()  # Create a new database session
#     try:
#         # Query all bookings from the database
#         bookings = db.query(BookingDB).all()
#         return bookings
#     finally:
#         db.close()  # Ensure the session is closed



# # Update the create_booking function
# @app.post("/bookings")
# def create_booking(
#     booking: DTOBooking, 
#     booking_service: BookingService = Depends(get_booking_service)
# ):
#     try:
#         new_booking = booking_service.create_booking(booking)
#         return {"message": "Booking successful", "id": new_booking.id}
#     except HTTPException:
#         raise
# def create_booking(booking: DTOBooking):
#     db = SessionLocal()  # Create a new database session
#     try:
#         # Check for existing bookings
#         existing_booking = db.query(BookingDB).filter(
#             BookingDB.date == booking.date,
#             BookingDB.time == booking.time
#         ).first()
#         if existing_booking:
#             raise HTTPException(status_code=400, detail="Slot already booked")

#         # Create a new booking instance
#         new_booking = BookingDB(
#             id=str(uuid.uuid4()),  # Generate a unique ID
#             name=booking.name,
#             email=booking.email,
#             date=booking.date,
#             time=booking.time
#         )
#         db.add(new_booking)  # Add the new booking to the session
#         db.commit()  # Commit the transaction
#         db.refresh(new_booking)  # Refresh the instance to get the updated data
#         return {"message": "Booking successful"}
#     finally:
#         db.close()  # Ensure the session is closed