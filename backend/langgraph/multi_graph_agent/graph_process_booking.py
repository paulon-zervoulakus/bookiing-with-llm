import re
import json
import traceback
from typing import Any, Dict, List, Literal
from datetime import datetime
from langgraph.graph import StateGraph
from langchain_core.messages import AIMessage, SystemMessage, HumanMessage, ToolMessage
from backend.langgraph.multi_graph_agent.states import SharedState
from backend.langgraph.multi_graph_agent.llm_setup import checkpointer, base_llm
from backend.database import SessionLocal
from backend.services.booking_service import BookingService
from backend.schema.booking_schema import BookingSchema
from backend.model.booking import BookingModel
from contextlib import contextmanager
from email_validator import validate_email, EmailNotValidError
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel

@tool
def extract_booking_information(name: str, email: str, schedule_date: str, schedule_time: str,
                                current_booking_info: dict = None) -> BookingSchema:
    """Return booking information based on the user's input, merged with current booking information.

    Analyze the user's message and extract:
    - name: The person's name (if mentioned)
    - email: The person's email address (if mentioned)
    - schedule_date: The desired date in YYYY-MM-DD format (if mentioned)
    - schedule_time: The desired time in 12-hour format with AM/PM (if mentioned)

    If any information is not provided by the user, preserve existing values from current_booking_info.
    If no existing value exists, use empty string "".

    Args:
        name (str): The name of the user
        email (str): The email of the user
        schedule_date (str): The date of the booking
        schedule_time (str): The time of the booking
        current_booking_info (dict): Current booking information from state
    """
    # Get current booking info or empty dict
    current_info = current_booking_info or {}

    return {
        "name": name if name else current_info.get("name", ""),
        "email": email if email else current_info.get("email", ""),
        "schedule_date": schedule_date if schedule_date else current_info.get("schedule_date", ""),
        "schedule_time": schedule_time if schedule_time else current_info.get("schedule_time", "")
    }

#@tool
# def save_booking_schedule(booking_info: BookingSchema) -> BookingSchema:
#     """Save booking schedule from user information"""
#     print(f"\n============================= save_booking_schedule")
#     # print(f"\nsave_booking_schedule:\n{booking_info["name"]}\n{booking_info["email"]}\n{booking_info["schedule_date"]}\n{booking_info["schedule_time"]}")
#     with get_booking_service() as booking_service:
#         try:
#             booking_dto = BookingModel(
#                 name=booking_info["name"],
#                 email=booking_info["email"],
#                 schedule_date=booking_info["schedule_date"],
#                 schedule_time=booking_info["schedule_time"]
#             )
#
#             new_booking = booking_service.create_booking(booking_dto)
#             booking_info["booking_id"] = new_booking.id
#             booking_info["booking_status"] = "confirmed"
#
#         except Exception as e:
#             booking_info["booking_status"] = "failed"
#             booking_info["error_message"] = f"{str(e)}\n{traceback.format_exc()}"
#     return booking_info


async def node_booking(state: SharedState) -> SharedState:
    """Entry point for the node_booking agent."""
    print(f"\n============================= node_booking")
    booking_form = {
        "name": state.get("booking_info", {}).get("name", ""),
        "email": state.get("booking_info", {}).get("email", ""),
        "schedule_date": state.get("booking_info", {}).get("schedule_date", ""),
        "schedule_time": state.get("booking_info", {}).get("schedule_time", "")
    }
    booking_status = state.get("booking_status", "")
    system_msg = SystemMessage(content=f"""<|begin_of_system|>
You are a precise and intelligent booking assistant whose primary role is to accurately classify user messages related to bookings.

GENERAL RULE: Your responsibility is to identify whether the user's message falls into one of these categories:
1. GET 
    - When user is asking for the booking details.
2. UPDATE 
    - When users are providing or updating details like name, email, date, or time
3. SAVING 
    - When users explicitly request to save or proceed with their booking.


CLASSIFICATION: Guidelines to follow
- Focus only on the semantic meaning of the message, not on formatting or style
- Look for specific booking-related keywords and phrases
- Pay attention to temporal indicators suggesting scheduling intentions
- Note any contact information being shared (names, emails)

CRITICAL AFFIRMATIVE RESPONSE HANDLING:
- The affirmative response contains additional text like "yes please proceed with booking", classify as SAVING

HERE IS THE ACTUAL {{booking_form}}:
{booking_form}

When analyzing a message, provide your classification with a brief justification of your selected category.
You will respond with one of the options only, with priority to the sequence below:
GET, UPDATE, SAVING
<|end_of_system|>""")

    llm_response = create_react_agent (
        model=base_llm,
        tools=[],
        prompt=system_msg

    ).invoke({"messages": [{"role": "user", "content": state.get("input_message", "")}]})

    # Parse the response and update the state
    try:
        # Extract the content from the response
        ai_messages = [msg for msg in llm_response['messages'] if isinstance(msg, AIMessage)]
        if ai_messages:
            last_ai_message = ai_messages[-1]
            content = last_ai_message.content

            # Simple parsing for the classification response
            if "GET" in content:
                booking_status = "GET"
            elif "UPDATE" in content:
                booking_status = "UPDATE"
            elif "SAVING" in content:
                booking_status = "SAVING"

        return {
            **state,
            "booking_status": booking_status
        }
    except Exception as e:
        print(f"🚨 Error processing LLM response: {str(e)}")
        return {**state, "messages": [AIMessage(content="Sorry, I encountered an error.")]}

async def node_get_booking_information(state: SharedState) -> SharedState:
    """This node is used to extract the booking information from the existing state."""
    print(f"\n- node_get_booking_information")
    ai_message = f"Here is your booking information: \n \
Name: {state.get('booking_info', {}).get('name', '[Missing]')}\n \
Email: {state.get('booking_info', {}).get('email', '[Missing]')}\n \
Schedule Date: {state.get('booking_info', {}).get('schedule_date', '[Missing]')}\n \
Schedule Time: {state.get('booking_info', {}).get('schedule_time', '[Missing]')}"

    return {
        **state,
        "messages": [AIMessage(content=ai_message)]
    }

async def node_update_form(state: SharedState) -> SharedState:
    """This node is used to update the booking information"""
    print(f"\n- node_update_form")

    # Get current date and time
    current_datetime = datetime.now()
    current_date = current_datetime.strftime("%Y-%m-%d")
    current_time = current_datetime.strftime("%I:%M %p")
    current_day = current_datetime.strftime("%A")

    system_msg = SystemMessage(content=f"""<|begin_of_system|>
You are a precise booking information extractor. Your task is to analyze user messages and extract ONLY the following booking information:

1. name: The person's full name
2. email: A valid email address
3. schedule_date: The booking date in YYYY-MM-DD format
4. schedule_time: The booking time in 12-hour format (e.g., "10:30 AM" or "2:00 PM")

IMPORTANT DATE HANDLING INSTRUCTIONS:
- For relative dates, convert them to actual dates based on today's date (2025-07-10):
  * "today" → "2025-07-10"
  * "tomorrow" → "2025-07-11"
  * "day after tomorrow" → "2025-07-12" 
  * "next week" → "2025-07-17" (7 days from today)
  * "next month" → "2025-08-10" (same day next month)
  * Weekdays like "Monday", "Tuesday", etc. → Convert to the next occurrence
  * "this Friday" → Convert to the coming Friday's date
  * "next Friday" → Convert to Friday of next week

TIME INTERPRETATION GUIDELINES:
- Convert all times to 12-hour format with AM/PM
- Handle variations like "morning" (9:00 AM), "noon" (12:00 PM), "afternoon" (2:00 PM), "evening" (6:00 PM)
- For vague times like "morning appointment", use 9:00 AM as default
- For expressions like "3 in the afternoon", convert to "3:00 PM"

CURRENT SYSTEM DATETIME:
- Current date: {current_date}
- Current time: {current_time}
- Current day: {current_day}
- Current datetime: {current_datetime.strftime("%Y-%m-%d %I:%M %p")}

EXTRACTION RULES:
1. Only extract information that is EXPLICITLY mentioned or clearly implied
2. Do NOT invent or assume information that isn't provided
3. Leave fields empty (empty string) if they are not mentioned
4. For partial information (like only a first name), extract what is available
5. Recognize both formal and casual expressions of dates and times
6. Handle corrections (e.g., "not Monday, but Tuesday" should extract Tuesday)

OUTPUT FORMAT:
You must respond with ONLY a JSON object containing the extracted fields. Do not include explanations, reasoning, or other text.

Example response format:
{{
  "name": "John Smith",
  "email": "john.smith@example.com",
  "schedule_date": "2025-07-15",z
  "schedule_time": "2:30 PM"
}}
<|end_of_system|>""")
    agent = create_react_agent (
        model=base_llm,
        tools=[],
        prompt=system_msg
    )
    llm_response = await agent.ainvoke({"messages": [{"role": "user", "content": state.get("input_message", "")}]})
    try:

        extracted_booking_info = json.loads(llm_response['messages'][-1].content)

        new_booking_info = {
            "name": extracted_booking_info.get("name") if extracted_booking_info.get("name","") and extracted_booking_info.get("name") != "" else state.get("booking_info", {}).get("name", ""),
            "email": extracted_booking_info.get("email") if extracted_booking_info.get("email","") and extracted_booking_info.get("name") != "" else state.get("booking_info", {}).get("email", ""),
            "schedule_date": extracted_booking_info.get("schedule_date") if extracted_booking_info.get("schedule_date","") and extracted_booking_info.get("schedule_date") != "" else state.get("booking_info", {}).get("schedule_date", ""),
            "schedule_time": extracted_booking_info.get("schedule_time") if extracted_booking_info.get("schedule_time","") and extracted_booking_info.get("schedule_time") != "" else state.get("booking_info", {}).get("schedule_time", "")
        }
        booking_status = state.get("booking_status", "")
        missing_fields = []
        for k, v in new_booking_info.items():
            if v is None or v == "":
                missing_fields.append(k)

        ai_message = f"Here is your updated booking information:\n \
Name: {new_booking_info.get('name', '[Missing]')}\n \
Email: {new_booking_info.get('email', '[Missing]')}\n \
Schedule Date: {new_booking_info.get('schedule_date', '[Missing]')}\n \
Schedule Time: {new_booking_info.get('schedule_time', '[Missing]')}"
        if len(missing_fields) == 0:
            ai_message += "\n\nShall I proceed with the booking? [yes/no]"
            booking_status = "CONFIRMATION"

        return {
            **state,
            "booking_info": new_booking_info,
            "booking_status": booking_status,
            "messages": [AIMessage(content=ai_message)]
        }
    except json.JSONDecodeError as e:
        print(e.msg)
        return {
            **state,
            "messages": [AIMessage(content="Sorry, I couldn't extract the booking information from your message.")]
        }

@contextmanager
def get_booking_service():
    """Context manager for booking service with automatic cleanup"""
    db = SessionLocal()
    try:
        yield BookingService(db)
    finally:
        db.close()

def save_booking_schedule(booking_info: dict) -> dict:
    """Save booking schedule to the database, the booking_info is a BookingSchema object coming from the state.

    Args:
        booking_info (BookingSchema): The booking information to save
    """
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
            booking_info["id"] = new_booking.id
            booking_info["booking_status"] = "confirmed"

        except Exception as e:
            booking_info["booking_status"] = "failed"
            booking_info["error_message"] = f"{str(e)}\n{traceback.format_exc()}"
    return booking_info

async def node_saving(state: SharedState) -> SharedState:
    """This node is used to save the booking information and proceed with the actual booking."""
    print(f"\n- node_saving")
    booking_form = {
        "name": state.get("booking_info", {}).get("name", ""),
        "email": state.get("booking_info", {}).get("email", ""),
        "schedule_date": state.get("booking_info", {}).get("schedule_date", ""),
        "schedule_time": state.get("booking_info", {}).get("schedule_time", "")
    }
    missing_fields = []

    for k,v in booking_form.items():
        if v is None or v == "":
            missing_fields.append(k)

    if len(missing_fields) > 0:
        missing_fields_str = ", ".join(missing_fields)
        content_msg = f"In order to proceed with booking, please provide the following missing detail(s): {missing_fields_str}"
        return {
            **state,
            "booking_status": "INCOMPLETE",
            "messages": [AIMessage(content=content_msg)]
        }


    # Now use the save_booking_schedule tool directly
    try:
        result = save_booking_schedule(booking_form)

        # Update the state with the result
        return {
            **state,
            "booking_status": "CONFIRMED",
            "booking_info": {
                "name": booking_form["name"],
                "email": booking_form["email"],
                "schedule_date": booking_form["schedule_date"],
                "schedule_time": booking_form["schedule_time"],
                "id": result.id if hasattr(result, 'id') else None,
                "booking_status": result.booking_status if hasattr(result, 'booking_status') else "confirmed"
            },
            "messages": [AIMessage(
                content=f"Successfully booked an appointment.\n\nHere are the details of your booked schedule: \nName: {booking_form['name']}\nEmail: {booking_form['email']}\nSchedule Date: {booking_form['schedule_date']}\nSchedule Time: {booking_form['schedule_time']}")]
        }
    except Exception as e:
        return {
            **state,
            "booking_status": "FAILED",
            "error_message": str(e),
            "messages": [
                AIMessage(content=f"Sorry, I encountered an error while trying to save your booking: {str(e)}")]
        }

def step_decision_making(state):
    if state.get("booking_status") == "GET":
        return "GET"
    elif state.get("booking_status") == "UPDATE":
        return "UPDATE"
    elif state.get("booking_status") == "SAVING":
        return "SAVING"
    else:
        return "UNKNOWN"

graph_process_booking = (
    StateGraph(SharedState)
    .add_node("node_booking", node_booking)
    .add_node("node_get_booking_information", node_get_booking_information)
    .add_node("node_update_form", node_update_form)
    .add_node("node_saving", node_saving)
    .add_conditional_edges(
        "node_booking",
        step_decision_making,
        {
            "GET": "node_get_booking_information",
            "UPDATE": "node_update_form",
            "SAVING": "node_saving",
        }
    )
    .set_entry_point("node_booking")
    .compile(checkpointer=checkpointer)
)