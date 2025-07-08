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
# --- Router Node ---
async def route_by_intents(state: SharedState) -> SharedState:
    print("Routing by intent...")
    print(f"\n PRE State: {state}")

    state["messages"] = [HumanMessage(content=state["input_message"])]

    classifier_result = await graph_intent_classifier.ainvoke(state, config)
    state.update(classifier_result)
    intent_list = state.get("intent")

    for intent in intent_list:        
        if intent == "identify":
            result = await graph_user_info_scraper.ainvoke(state, config)
            state.update(result)
        elif intent == "inquiring":
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

# async def end_collate(state: SharedState) -> SharedState:
#     print(f"\n===== end collate =====")
#     if "inquiring" in state["intent"]:
#         # call summary for inquiry
#         result = await graph_summary_inquiry.ainvoke(state, config)
#         state.update(result)
#     #
#     # elif "bookings" in state["intent"]:
#     #     result = await graph_summary_booking.ainvoke(state, config)
#     #     state.update(result)
#     # else:
#     #     result = await graph_summary_fallback.ainvoke(state, config)
#     #     state.update(result)
#
#     print(f"\n===== POST State: {state}")
#     return state
# --- Main Graph ---
def build_main_graph():    
    graph = StateGraph(SharedState)
    graph.add_node("router", route_by_intents)
    # graph.add_node("end_collate", end_collate)
    # graph.add_edge("router", "end_collate")
    graph.set_entry_point("router")
    # graph.set_finish_point("end_collate")
    return graph.compile(checkpointer=checkpointer)
