from langgraph.graph import StateGraph
from langchain_core.messages import HumanMessage
from typing import TypedDict, List, Optional

from backend.langgraph.multi_graph_agent.graph_user_info_scraper import graph_user_info_scraper
from backend.langgraph.multi_graph_agent.graph_human_question import graph_human_question
from backend.langgraph.multi_graph_agent.graph_intent_classifier import graph_intent_classifier
from backend.langgraph.multi_graph_agent.graph_process_booking import graph_process_booking
from backend.langgraph.multi_graph_agent.graph_summary_booking import graph_summary_booking
from backend.langgraph.multi_graph_agent.graph_summary_inquiry import graph_summary_inquiry
from backend.langgraph.multi_graph_agent.graph_fallback import graph_fallback
from backend.langgraph.multi_graph_agent.states import SharedState
from backend.langgraph.multi_graph_agent.llm_setup import config
from backend.langgraph.multi_graph_agent.llm_setup import checkpointer

_current_user_info = {"name": "", "email": ""}
# Function to update user info
def update_user_info(name: str, email: str):
    """Update the global user info"""
    global _current_user_info
    _current_user_info["name"] = name
    _current_user_info["email"] = email

# --- Router Node ---
async def route_by_intents(state: SharedState) -> SharedState:
    print("Routing by intent...")

    global _current_user_info
    if "booking_info" not in state:
        state["booking_info"] = {"name": _current_user_info["name"], "email": _current_user_info["email"]}
    else:
        # If booking_info exists but name and email is empty, set default
        if "name" not in state.get("booking_info", {}):
            state["booking_info"]["name"] = _current_user_info["name"]
        if "email" not in state.get("booking_info", {}):
            state["booking_info"]["email"] = _current_user_info["email"]


    print(f"\n PRE State: {state}")

    state["messages"] = [HumanMessage(content=state["input_message"])]

    classifier_result = await graph_intent_classifier.ainvoke(state, config)
    state.update(classifier_result)
    intent_list = state.get("intent")

    for intent in intent_list:        
        # if intent == "identify":
        #     result = await graph_user_info_scraper.ainvoke(state, config)
        #     state.update(result)
        if intent == "inquiring":
            result = await graph_human_question.ainvoke(state, config)
            state.update(result)
        elif intent == "fallback":
            result = await graph_fallback.ainvoke(state, config)
            state.update(result)
        elif intent == "bookings":
            result = await graph_process_booking.ainvoke(state, config)
            state.update(result)

    print(f"\n POST State: {state}")
    return state


def build_main_graph():
    graph = StateGraph(SharedState)
    graph.add_node("router", route_by_intents)
    graph.set_entry_point("router")
    return graph.compile(checkpointer=checkpointer)
