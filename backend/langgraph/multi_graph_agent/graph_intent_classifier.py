"""This is the Intent Classifier graph"""
from datetime import datetime
from langgraph.graph import StateGraph
from langchain.prompts import PromptTemplate
from langchain_core.messages import AIMessage
from backend.langgraph.multi_graph_agent.llm_setup import base_llm
from backend.langgraph.multi_graph_agent.states import SharedState
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableConfig

# @tool
def tool_last_ai_message(state: SharedState) -> str:
    """Return the last AI message in the state"""
    if state.get("messages") and len(state.get("messages")) > 0:
        ai_messages = [msg for msg in state.get("messages") if isinstance(msg, AIMessage)]
        if ai_messages:
            return ai_messages[-1].content
        else:
            return ""
    else:
        return ""


def prompt_modifier(ai_last_response):
    """Prompt modifier is used for SystemMessage."""
    return f"""
You are a strict intent classifier. 

IMPORTANT: Read the user's message carefully. Are they GIVING you information or ASKING for information?

AWARENESS: You always need to consider the previews AI Response, use this conversation history to identify if the message is an answer to the previews conversation.

INTENT DEFINITIONS:
1. "bookings" → User wants to make/schedule an appointment interview or updating a booking information or retrieving booking information, everything there is for booking, appointment, schedule or interview.
2. "inquiring" → User asks about Canada migration, Canadian culture, living in Canada, Documents needed for application to migrate in Canada, everything their is to know about Canada.
3. "fallback" → Everything else that is not classified as bookings or inquiring will be classified as fallback.  

ONLY classify as "bookings" if the user is:
- Telling you or asking you to schedule an appointment interview or update a booking or retrieve booking information.

EXAMPLES:
What is my name? -> fallback
Whats my booking email? -> bookings
Who am I? -> fallback
Book me a schedule tomorrow -> bookings
What is the primary language of Canada? -> inquiring
What is the primary language of Russia? -> fallback
What are the requirements for the interview? -> bookings

PREVIEWS AI RESPONSE:
{ai_last_response}

RESPONSE FORMAT:
Return ONLY one of the intent option above. Do not return any other information besides  from the above options given.
"""

# # Create the LCEL chain
# prompt = PromptTemplate(
#     input_variables=["message","tool_last_ai_message"],
#     template=prompt_modifier() + "\n\nInput: {message}\n→"
# )

# Modern LCEL approach
# intent_chain = prompt | base_llm | tool_last_ai_message | StrOutputParser()


async def node_intent_classifier(state: SharedState) -> SharedState:
    """Node intent classifier."""
    print(f"\n============================= node_intent_classifier")

    print(f"\nTime check\n - before llm: node_intent_classifier")
    start_time = datetime.now()

    ai_last_response = tool_last_ai_message(state)

    prompt = PromptTemplate(
        input_variables=["message","ai_last_response"],
        template=prompt_modifier(ai_last_response) + "\n\nInput: {message}\n→"
    )

    intent_chain = prompt | base_llm | StrOutputParser()

    llm_result = await intent_chain.ainvoke({
        "message": state["input_message"]
    })
    # llm_result = ""
    # chunk_count = 0
    # async for chunk in intent_chain.astream({"message": state["input_message"]}, config, stream_mode="update"):
    #     # for node_name, node_result in chunk.items():
    #     llm_result += chunk
    #     chunk_count += 1

    result_content = [item.strip() for item in llm_result.split(",")]

    # Validation and fallback
    try:
        updated_intent_result=[]
        for intent in result_content:
            if intent not in ["identify", "bookings", "inquiring", "fallback"]:
               updated_intent_result.append("fallback")
            else:
                updated_intent_result.append(intent)
        # Remove duplicates by converting to a set and back to a list
        updated_intent_result = list(set(updated_intent_result))

        # Define the priority order (highest priority first)
        priority_order = ["inquiring", "bookings", "fallback"]

        # Sort the list according to the priority
        updated_intent_result.sort(
            key=lambda x: priority_order.index(x) if x in priority_order else len(priority_order))

        result_content = updated_intent_result

        if not isinstance(result_content, list) or not result_content:
            result_content = ["fallback"]
    except Exception as e:
        print(f"Error processing intent: {e}")
        result_content = ["fallback"]

    # Always add fallback intent if the intent is only indentify
    if len(result_content) == 1 and result_content[0] == "identify":
        result_content.append("fallback")

    print(f"\nIntent List: {result_content}")

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\nTime check\n - after llm: node_intent_classifier - time: {elapsed:.3f}")

    return {
        **state,
        "intent": result_content,
        "short_message": "Node Intent Classifier"
    }

# graph_intent_classifier = (
#     StateGraph(SharedState)
#     .add_node("node_intent_classifier", node_intent_classifier)
#     .set_entry_point("node_intent_classifier")
#     .compile()
# )