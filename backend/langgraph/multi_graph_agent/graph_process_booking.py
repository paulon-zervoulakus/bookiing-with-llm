import re
import json
import traceback
from typing import Any, Dict, List
from datetime import datetime
from langgraph.graph import StateGraph
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage
from backend.langgraph.multi_graph_agent.states import SharedState
from backend.langgraph.multi_graph_agent.llm_setup import checkpointer, base_llm
from backend.database import SessionLocal
from backend.services.booking_service import BookingService
from backend.schema.booking_schema import BookingSchema
from backend.model.booking import BookingModel
from contextlib import contextmanager
from email_validator import validate_email, EmailNotValidError

@contextmanager
def get_booking_service():
    """Context manager for booking service with automatic cleanup"""
    db = SessionLocal()
    try:
        yield BookingService(db)
    finally:
        db.close()

def save_booking_schedule(booking_info: BookingSchema) -> BookingSchema:
    """Save booking schedule from user information"""
    print(f"\n============================= save_booking_schedule")
    # print(f"\nsave_booking_schedule:\n{booking_info["name"]}\n{booking_info["email"]}\n{booking_info["schedule_date"]}\n{booking_info["schedule_time"]}")
    with get_booking_service() as booking_service:
        try:
            booking_dto = BookingModel(
                name=booking_info["name"],
                email=booking_info["email"],
                schedule_date=booking_info["schedule_date"],
                schedule_time=booking_info["schedule_time"]
            )

            new_booking = booking_service.create_booking(booking_dto)
            booking_info["booking_id"] = new_booking.id
            booking_info["booking_status"] = "confirmed"

        except Exception as e:
            booking_info["booking_status"] = "failed"
            booking_info["error_message"] = f"{str(e)}\n{traceback.format_exc()}"
    return booking_info

async def node_analyze_message_and_scrape_booking_info(state: SharedState) -> SharedState:
    """Handle the complete booking flow: analysis -> validation -> booking creation"""
    print(f"\n============================= node_analyze_message_and_scrape_booking_info")

    print(f"\nTime check\n - before llm: node_analyze_message_and_scrape_booking_info")
    start_time = datetime.now()
    system_msg = SystemMessage(content="""
You are a strict Schedule Booker Analyzer.

Return only a valid JSON object. No text, no formatting, no explanation.

Extract the following booking details:
- name
- email
- schedule_date (in YYYY-MM-DD)
- schedule_time (12-hour format with AM/PM)

If any field is missing, use "".

Format:
{
  "booking_info": {
    "name": "...",
    "email": "...",
    "schedule_date": "...",
    "schedule_time": "..."
  }
}
""")
    llm_response = await base_llm.ainvoke([
        system_msg,
        HumanMessage(content=state["input_message"])
    ])
    try:
        content_obj = json.loads(llm_response.content.strip())
        print(f" - content_obj: {content_obj}")
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"\nTime check\n - after llm: node_analyze_message_and_scrape_booking_info - time: {elapsed:.3f}")
        return { **state, "booking_info": content_obj["booking_info"] }
    except json.JSONDecodeError:
        print("🚨 LLM returned unexpected content:\n", llm_response.content)
        return { **state }

async def node_validate_booking_information(state: SharedState) -> SharedState:
    print(f"\n============================= node_validate_booking_information")
    def is_date_invalid(date_str):
        if not date_str:
            return True
        try:
            datetime.strptime(date_str, "%Y-%m-%d")
            return False
        except ValueError:
            return True
    def is_time_invalid(time_str):
        if not time_str:
            return True
        try:
            datetime.strptime(time_str, "%I:%M %p")
            return False
        except ValueError:
            return True
    def normalize_time_format(time_str: str) -> str:
        """
        Normalize time string to 12-hour format with AM/PM, e.g., "9:00 PM"
        """
        time_str = time_str.strip().lower().replace('.', '')
        try:
            # Try 24-hour format first (e.g., 21:00)
            time_obj = datetime.strptime(time_str, "%H:%M")
        except ValueError:
            try:
                # Try 12-hour format (e.g., 9 PM, 9pm, 9:00pm)
                time_obj = datetime.strptime(time_str, "%I:%M %p")
            except ValueError:
                try:
                    # Try short 12-hour (e.g., 9pm)
                    time_obj = datetime.strptime(time_str, "%I%p")
                except ValueError:
                    return time_str  # Return as-is if all parsing fails
        return time_obj.strftime("%I:00 %p")  # Or "%I:00 %p" for Windows

    incomplete_fields = []
    email_pattern = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    booking_info = state["booking_info"]
    if booking_info["name"] is None or booking_info["name"] == "":
        incomplete_fields.append("name")
    if booking_info["email"] is None or booking_info["email"] == "":
        incomplete_fields.append("email")
    else:
        # Check if email is valid
        try:
            email_obj = validate_email(booking_info["email"])
            if not re.match(email_pattern, booking_info["email"]):
                incomplete_fields.append("email_invalid")
        except EmailNotValidError as e:
            incomplete_fields.append("email")

    add_date_if_invalid = lambda date_str, incomplete_fields: incomplete_fields.append("schedule_date") if is_date_invalid(date_str) else None
    add_date_if_invalid(booking_info["schedule_date"], incomplete_fields)

    add_time_if_invalid = lambda time_str, incomplete_fields: incomplete_fields.append("schedule_time") if is_time_invalid(time_str) else None
    add_time_if_invalid(normalize_time_format(booking_info["schedule_time"]), incomplete_fields)

    return {
        **state,
        "incomplete_fields": incomplete_fields
    }

async def node_booking_form(state: SharedState) -> SharedState:
    print(f"\n============================= node_booking_form")

    try:
        # check if there is a missing field
        if state["incomplete_fields"] and len(state["incomplete_fields"])>0:
            missing_msg = "\n".join(f"{k}: \"{v}\"" for k, v in state["booking_info"].items())
            content_msg = f"In order to proceed with booking, please provide the following missing detail(s):\n{missing_msg}"
            return {
                **state,
                "booking_status": "incomplete",
                "messages": [AIMessage(content=content_msg)]
            }
    except json.JSONDecodeError as e:
        return {
            **state,
            "booking_status": "error",
            "error_message": e.msg,
            "messages": [AIMessage(content="In order to proceed with booking, please provide the following missing detail(s) [name, email, schedule date, schedule time]")]
        }

async def node_save_booking(state: SharedState) -> SharedState:
    print(f"\n============================= node_save_booking")
    save_booking = save_booking_schedule(state["booking_info"])
    if save_booking["booking_status"] == "confirmed":
        return {
            **state,
            "booking_status": "confirmed",
            "booking_info": save_booking,
            "messages": [
                AIMessage(content="Sucessfully booked a schedule"),
                AIMessage(content=f"Here are the details newly booked schedule: \n {save_booking}")
            ]
        }
    else:
        missing_msg = "\n".join(f"{k}: \"{v}\"" for k, v in state["booking_info"].items())
        content_msg = f"In order to proceed with booking, please provide the following missing detail(s):\n{missing_msg}"
        return {
            **state,
            "booking_status": "failed",
            "error_message": save_booking["error_message"],
            "messages": [AIMessage(content=content_msg)]
        }

def decision_making(state):
    if state.get("incomplete_fields"):
        return "node_booking_form"
    else:
        return "node_save_booking"

graph_process_booking = (
    StateGraph(SharedState)
    .add_node("node_analyze_message_and_scrape_booking_info", node_analyze_message_and_scrape_booking_info)
    .add_node("node_validate_booking_information", node_validate_booking_information)
    .add_node("node_booking_form", node_booking_form)  # Make sure this node exists
    .add_node("node_save_booking", node_save_booking)  # Make sure this node exists
    .add_edge("node_analyze_message_and_scrape_booking_info", "node_validate_booking_information")  # <-- ADD THIS LINE
    .add_conditional_edges(
        "node_validate_booking_information",
        decision_making
    )
    .set_entry_point("node_analyze_message_and_scrape_booking_info")
    .compile(checkpointer=checkpointer)
)