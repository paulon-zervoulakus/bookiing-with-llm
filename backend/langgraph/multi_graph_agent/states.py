
import json
from typing import Annotated, Any, List, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph import add_messages

def merge_booking(left: Any, right: Any):
    """This function merges two bookings"""
    if not right:
        return left
    return {**left, **right}

class BookingInfoState(TypedDict):
    """BookingInfoState Schema"""
    name: Optional[str]
    email: Optional[str]
    schedule_date: Optional[str] = None
    schedule_time: Optional[str] = None
    profession: Optional[str] = None
    booking_id: Optional[int] = 0    

class SharedState(TypedDict, total=False):
    """SharedState Schema"""
    intent: Annotated[List[str], lambda prev, new: new if new is not None else prev]
    input_message: Annotated[Optional[str], lambda prev, new: new] # This is a raw string from human
    human_inquiry: Annotated[Optional[str], lambda prev, new: new] # This is a raw string from human
    chunk_answer_from_inquiry: Annotated[Optional[str], lambda prev, new: new] # Value of this will be coming from AI
    booking_info: Annotated[BookingInfoState, merge_booking]
    booking_status: Annotated[Optional[str], lambda prev, new: new]
    incomplete_fields: Annotated[List[str], lambda prev, new: new]
    error_message: Annotated[Optional[str], lambda prev, new: new]
    messages: Annotated[List[BaseMessage], add_messages]

# class GraphUserState(TypedDict):    
#     user_info: Annotated[UserInfo, merge_user_info]
#     input_message: Annotated[Optional[str], lambda prev, new: new] # This is a raw string from human
#     human_inquiry: Annotated[Optional[str], lambda prev, new: new] # Value here was cleaned by AI
#     inquiry_answer: Annotated[Optional[str], lambda prev, new: new] # Value of this will be coming from AI
#     intent: Annotated[List[str], merge_intent] 
#     messages: Annotated[List[BaseMessage], add_messages]
#     last_node: Annotated[Optional[str], lambda prev, new: new]    
#     error_message: Annotated[Optional[str], lambda prev, new: new]
#     incomplete_fields: Annotated[List[str], lambda prev, new: new]