import datetime
from typing import Any, Dict, List
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.graph import StateGraph
from backend.langgraph.multi_graph_agent.states import SharedState
from backend.langgraph.multi_graph_agent.llm_setup import base_llm, checkpointer
async def collate_end_booking(state: SharedState) -> SharedState:
    print(f"\n===== collate_end_booking =====")
    """
    Finalize and format the booking response message for the user.
    
    Args:
        booking_status: Status of the booking ('confirmed', 'incomplete', 'failed', 'error')
        booking_info: Dictionary containing user booking information
        incomplete_fields: List of missing or invalid fields (optional)
        booking_reference: Booking reference ID if confirmed (optional)
        error_message: Custom error message if needed (optional)
    
    Returns:
        Dictionary with formatted response for the user
    """
    
    def format_booking_info(info: Dict[str, Any]) -> str:
        """Format booking info for display"""
        formatted_info = []
        field_labels = {
            'name': 'Name',
            'email': 'Email',
            'schedule_date': 'Date',
            'schedule_time': 'Time'
        }
        
        for key, value in info.items():
            if value:  # Only include non-empty values
                label = field_labels.get(key, key.replace('_', ' ').title())
                formatted_info.append(f"• {label}: {value}")
        
        return '\n'.join(formatted_info)
    
    def format_missing_fields(fields: List[str]) -> str:
        """Format missing fields list for display"""
        field_labels = {
            'name': 'Full Name',
            'email': 'Email Address',
            'schedule_date': 'Preferred Date',
            'schedule_time': 'Preferred Time'
        }
        
        formatted_fields = []
        for field in fields:
            label = field_labels.get(field, field.replace('_', ' ').title())
            formatted_fields.append(f"• {label}")
        
        return '\n'.join(formatted_fields)
    
    # Generate timestamp for booking
    current_time = datetime.time().strftime("%Y-%m-%d %H:%M:%S")
    
    if state["booking_status"] == "confirmed":
        # Successful booking confirmation
        system_message = f"""✅ **Booking Confirmed Successfully!**

Thank you for your booking. Here are your confirmed details:

{format_booking_info(state["booking_info"])}

📧 A confirmation email has been sent to your email address.
📱 You will receive an SMS reminder 24 hours before your appointment.

**Booking Reference:** {'SCHED-ID-' + state["booking_info"]["booking_id"] or 'BOOK-' + str(hash(str(state["booking_info"])))[:8].upper()}
**Confirmed at:** {current_time}

If you need to make any changes or have questions, please contact us with your booking reference number."""      
    
    elif state["booking_status"] == "incomplete":
        # Missing or incomplete information
        missing_fields_text = format_missing_fields(state["incomplete_fields"]) if state["incomplete_fields"] and len(state["incomplete_fields"])>0 else "Required booking information"
        
        system_message = f"""⚠️ **Additional Information Required**

To complete your booking, please provide the following details:

{missing_fields_text}

Current information received:
{format_booking_info(state["booking_info"]) if state["booking_info"] else 'None provided yet'}

Please provide the missing information and I'll process your booking immediately."""
    
    elif state["booking_status"] == "failed":
        # Booking failed due to availability or validation issues
        system_message = f"""❌ **Booking Could Not Be Completed**

Unfortunately, we couldn't process your booking request due to the following:

{state["error_message"] or 'The requested time slot may not be available or there was a validation error.'}

Your provided information:
{format_booking_info(state["booking_info"])}

**What you can do:**
• Try selecting a different date or time
• Contact us directly for alternative options
• Check our availability calendar

Would you like to try booking for a different time?"""
        
    elif state["booking_status"] == "error":
        # System error or unexpected issue
        system_message = f"""🔧 **System Error**

We apologize, but there was a technical issue processing your booking request.

{state["system_message"] or 'Please try again in a few moments or contact our support team.'}

Your information has been temporarily saved:
{format_booking_info(state["booking_info"])}

**Error occurred at:** {current_time}

Please try submitting your booking again, or contact our support team if the problem persists."""    

    else:
        # Unknown status - fallback
        system_message = f"""❓ **Booking Status Unknown**

We received your booking request but couldn't determine the final status.

Your information:
{format_booking_info(state["booking_info"])}

Please contact our support team to verify your booking status."""

    response = await base_llm.ainvoke([
        system_message,
        HumanMessage(content=state["input_message"])
    ])

    return {
        **state,
        "messages": [AIMessage(response.content.strip())]
    }

    
graph_summary_booking = (
    StateGraph(SharedState)
    .add_node("collate_end_booking", collate_end_booking)
    .set_entry_point("collate_end_booking")
    .compile(checkpointer=checkpointer)
)