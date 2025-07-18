"""This is the main graph"""
from langgraph.graph import StateGraph, START, END
from backend.langgraph.multi_graph_agent.graph_human_question import graph_human_question
from backend.langgraph.multi_graph_agent.graph_intent_classifier import  node_intent_classifier
from backend.langgraph.multi_graph_agent.graph_process_booking import graph_process_booking
from backend.langgraph.multi_graph_agent.graph_fallback import graph_fallback
from backend.langgraph.multi_graph_agent.states import SharedState, BookingInfoState
from backend.langgraph.multi_graph_agent.llm_setup import checkpointer
from langchain_core.runnables import RunnableConfig

async def node_initializer(state: SharedState, config: RunnableConfig) -> SharedState:
    """Node that initializes the state"""
    print(f"\n============================= node_initializer")
    if "booking_info" not in state:
        state["booking_info"] = BookingInfoState(
            name=config["configurable"]["user"]["name"],
            email=config["configurable"]["user"]["email"]
        )
    else:
        # If booking_info exists but name and email empty, set default
        if "name" not in state.get("booking_info", {}):
            state["booking_info"]["name"] = config["configurable"]["user"]["name"]
        if "email" not in state.get("booking_info", {}):
            state["booking_info"]["email"] = config["configurable"]["user"]["email"]

    state["short_message"] = "Node Initializer"
    # print(f"\n PRE State: {state}")
    return state


async def node_inquiring(state: SharedState, config: RunnableConfig) -> SharedState:
    """Node that handles inquiries"""
    print(f"\n============================= node_inquiring")
    result = await graph_human_question.ainvoke(state, config)
    state.update(result)
    return state


async def node_fallback(state: SharedState, config: RunnableConfig) -> SharedState:
    """Node that handles fallback"""
    print(f"\n============================= node_fallback")
    result = await graph_fallback.ainvoke(state, config)
    state.update(result)
    return state

async def node_process_booking(state: SharedState, config: RunnableConfig) -> SharedState:
    """Node that handles booking"""
    print(f"\n============================= node_process_booking")
    result = await graph_process_booking.ainvoke(state, config)
    state.update(result)
    return state

async def route_by_intents(state: SharedState):
    """Route the input message to the appropriate graph based on the intent"""
    print("Routing by intent...")
    intent_list = state.get("intent")
    if not intent_list:
        return "end"

    intent_result = ""
    for intent in intent_list:
        if intent == "inquiring":
            intent_result = "inquiring"
            intent_list.remove(intent)
            state.update({
                **state,
                "intent": intent_list,
            })
            break
        elif intent == "fallback":
            intent_result = "fallback"
            intent_list.remove(intent)
            state.update({
                **state,
                "intent": intent_list,
            })
        elif intent == "bookings":
            intent_result = "bookings"
            intent_list.remove(intent)
            state.update({
                **state,
                "intent": intent_list,
            })
            break
        else:
            intent_result = "end"
    return intent_result


async def router_node(state: SharedState) -> SharedState:
    """Router that consumes intents as they're processed"""
    intent_list = state.get("intent", [])
    
    if not intent_list:
        return {
            **state,
            "next_action": "end"
        }
    
    # Take the first intent and remove it from the list
    current_intent = intent_list[0]
    remaining_intents = intent_list[1:]

    return {
        **state,
        "intent": remaining_intents,  # Update with remaining intents
        "next_action": current_intent,
        "current_processing_intent": current_intent,
        "short_message": f"Router Node - {current_intent}"
    }

def route_after_router(state: SharedState) -> str:
    """Simple routing function"""
    return state.get("next_action", "end")

# Handler nodes should NOT modify intents
async def inquiring_handler(state: SharedState) -> SharedState:
    """Handle inquiring intent"""
    result = await graph_human_question.ainvoke(state)
    state["short_message"] = "Inquiring Handler"
    return {
        **state,
        **result
    }

async def fallback_handler(state: SharedState) -> SharedState:
    """Handle fallback intent"""
    result = await graph_fallback.ainvoke(state)
    state["short_message"] = "Fallback Handler"
    return {
        **state,
        **result
    }

async def bookings_handler(state: SharedState) -> SharedState:
    """Handle bookings intent"""
    # First scrape user info
    result = await graph_process_booking.ainvoke(state)
    state["short_message"] = "Booking Handler"
    return {
        **state,
        **result
    }

def build_main_graph():
    """Build graph with proper looping"""
    graph = StateGraph(SharedState)
    
    # Add nodes
    graph.add_node("init", node_initializer)
    graph.add_node("classify_intent", node_intent_classifier)
    graph.add_node("router", router_node)
    graph.add_node("inquiring", inquiring_handler)
    graph.add_node("fallback", fallback_handler)
    graph.add_node("bookings", bookings_handler)
    
    # Add edges
    graph.add_edge(START, "init")
    graph.add_edge("init", "classify_intent")
    graph.add_edge("classify_intent", "router")
    
    # Conditional edges from router
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {
            "inquiring": "inquiring",
            "fallback": "fallback",
            "bookings": "bookings",
            "end": END
        }
    )
    
    # ✅ Loop back to router
    graph.add_edge("inquiring", "router")
    graph.add_edge("fallback", "router")
    graph.add_edge("bookings", "router")
    
    return graph.compile(checkpointer=checkpointer)