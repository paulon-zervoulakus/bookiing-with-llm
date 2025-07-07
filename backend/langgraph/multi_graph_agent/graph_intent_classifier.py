import json
from typing import Literal, Optional
from pydantic import BaseModel
from datetime import datetime
from langgraph.graph import StateGraph
from langgraph.prebuilt import create_react_agent
from typing import Any, List
from langchain.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from backend.langgraph.multi_graph_agent.llm_setup import base_llm
from backend.langgraph.multi_graph_agent.states import SharedState
from backend.langgraph.multi_graph_agent.llm_setup import checkpointer, config

def prompt_modifier():
    return """
You are a strict intent classifier. 

IMPORTANT: Read the user's message carefully. Are they GIVING you information or ASKING for information?

📌 INTENT DEFINITIONS:
1. "identify" → User is GIVING/STATING their personal information (name, email, job, etc.)
   - Examples: "I am John", "My name is Sarah", "I'm a doctor"
   - NOT for questions like "Who am I?" or "What's my name?"

2. "bookings" → User wants to make/schedule an appointment
3. "inquiring" → User asks about Canada migration
4. "fallback" → Everything else, including questions about themselves

📌 NEVER classify as "identify" if the user is:
- Asking "Who am I?"
- Asking "What is my name?"
- Asking any question about themselves

📌 ONLY classify as "identify" if the user is:
- Telling you their name
- Sharing their profession
- Providing personal details

📌 EXAMPLES:
"I'm John Smith" → identify
"What is my name?" → fallback
"Who am I?" → fallback
"My name is Sarah" → identify

📌 RESPONSE FORMAT:
Return ONLY a string of intent/s separated by comma (,) without any spaces.
"""

# Create the LCEL chain
prompt = PromptTemplate(
    input_variables=["message"],
    template=prompt_modifier() + "\n\nInput: {message}\n→"
)

# Modern LCEL approach
intent_chain = prompt | base_llm | StrOutputParser()

async def node_intent_classifier(state: SharedState) -> SharedState:
    print(f"\n============================= node_intent_classifier")

    print(f"\nTime check\n - before llm: node_intent_classifier")
    start_time = datetime.now()
    
    # Invoke the LCEL chain
    result = await intent_chain.ainvoke({"message": state["input_message"]})
    
    result_content = [item.strip() for item in result.split(",")]

    # Validation and fallback
    try:
        if not isinstance(result_content, list) or not result_content:
            result_content = ["fallback"]
    except Exception as e:
        print(f"Error processing intent: {e}")
        result_content = ["fallback"]

    # Always add fallback intent if the intent is only indentify
    # if len(result_content) == 1 and result_content[0] == "identify":
    #     result_content.append("fallback")

    print(f"\nIntent List: {result_content}")

    elapsed = (datetime.now() - start_time).total_seconds()
    print(f"\nTime check\n - after llm: node_intent_classifier - time: {elapsed:.3f}")
    return { **state, "intent": result_content }

graph_intent_classifier = (
    StateGraph(SharedState)
    .add_node("node_intent_classifier", node_intent_classifier)
    .set_entry_point("node_intent_classifier")
    .compile()
)